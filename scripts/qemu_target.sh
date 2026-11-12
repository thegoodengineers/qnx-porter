#!/usr/bin/env bash
# Build, start and stop the QNX 8.0 QEMU target (x86_64, or aarch64le virt) that qnx-porter runs tests on.
# Uses QNX's own mkqnximage; adds the two fixes we needed on SDP 8.0 build 141 (see docs/LEARNINGS.md).
#
#   sudo scripts/qemu_target.sh net     # once per boot (WSL: after every `wsl --shutdown`): bridge + DHCP
#   scripts/qemu_target.sh build        # make the image in $IMAGE_DIR
#   scripts/qemu_target.sh start        # boot headless and wait for ssh
#   scripts/qemu_target.sh status|stop|restart   # restart: for a target that stopped answering
# QNX_TARGET_ARCH=aarch64le selects the 64-bit Arm target (needs the SDP's qemuvirt BSP package).
set -euo pipefail

ARCH=${QNX_TARGET_ARCH:-x86_64}
if [ "$ARCH" = x86_64 ]; then
    IP=${QNX_TARGET_IP:-172.31.1.11}; IMAGE_DIR=${IMAGE_DIR:-$HOME/qnx-images/qemu}
else
    IP=${QNX_TARGET_IP:-172.31.1.12}; IMAGE_DIR=${IMAGE_DIR:-$HOME/qnx-images/qemu-$ARCH}
fi
SSH=(ssh -o BatchMode=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR
     -o ConnectTimeout=5 "root@$IP")

sdp() {
    if [ -z "${QNX_HOST:-}" ]; then
        # shellcheck disable=SC1090
        source "${QNX_SDP:-$HOME/qnx800}/qnxsdp-env.sh" >/dev/null
    fi
}

case "${1:-}" in
net)
    [ "$EUID" = 0 ] || { echo "run as root: sudo $0 net"; exit 1; }
    user=${SUDO_USER:-${2:-}}
    home=$(getent passwd "${user:-root}" | cut -d: -f6)
    command -v dnsmasq >/dev/null || apt-get install -y -q dnsmasq-base
    [ -n "$user" ] && adduser "$user" kvm >/dev/null  # mkqnximage's runimage asks for this; KVM makes QEMU fast
    # QNX's net.sh sets up br0 and bridge.conf. Its dnsmasq call uses --except-interface=lo0, which on Linux
    # (and WSL, whose lo carries 10.255.255.254) collides; start our own dnsmasq instead. It also answers DNS on
    # br0 (forwarding to the host's resolver), so tests that read the system's name servers find one.
    "${home}/qnx800/host/common/mkqnximage/qemu/net.sh" /usr/lib/qemu/qemu-bridge-helper /etc/qemu/bridge.conf nat \
        2>/dev/null || true
    pgrep -f 'dnsmasq --interface=br0' >/dev/null ||
        dnsmasq --interface=br0 --bind-interfaces --except-interface=lo --dhcp-range=172.31.1.2,172.31.1.254
    ip -4 addr show br0 | grep -q 172.31.1.1 && echo "br0 ready"
    ;;
build)
    sdp
    [ -f ~/.ssh/id_ed25519.pub ] || ssh-keygen -q -t ed25519 -N '' -f ~/.ssh/id_ed25519
    mkdir -p "$IMAGE_DIR" && cd "$IMAGE_DIR"
    [ -d local ] || mkqnximage --noprompt --type=qemu --arch="$ARCH" --ip="$IP" --hostname="qnx-porter-$ARCH" \
        --ssh-ident="$HOME/.ssh/id_ed25519.pub" --data-size=5000 --data-inodes=40000 --ram=2G --cpu=4
    # SDP 8.0's sshd (OpenSSH 10) also needs sshd-auth; mkqnximage only copies sshd-session. Without this
    # sshd exits at boot with "/usr/libexec/sshd-auth does not exist or is not executable".
    if ! grep -q sshd-auth local/snippets/ifs_files.custom; then
        printf '\n# qnx-porter: sshd needs sshd-auth at its default path\n%s\n' \
            '[perms=555] /usr/libexec/sshd-auth=usr/libexec/sshd-auth' >> local/snippets/ifs_files.custom
    fi
    MKQNXIMAGE_NOPROMPT=1 mkqnximage --noprompt --build
    ;;
start)
    sdp
    cd "$IMAGE_DIR"
    # setsid: QEMU must outlive this shell (a plain background job dies with the WSL session)
    MKQNXIMAGE_NOPROMPT=1 setsid nohup mkqnximage --run=-h >"$IMAGE_DIR/../run.log" 2>&1 </dev/null &
    for _ in $(seq 1 30); do
        sleep 3
        if "${SSH[@]}" uname -a 2>/dev/null; then
            # The image's /etc/resolv.conf links to dhcpcd's file, which a static address never creates.
            "${SSH[@]}" "mkdir -p /data/var/dhcpcd; [ -s /data/var/dhcpcd/resolv.conf ] ||
                echo 'nameserver ${IP%.*}.1' > /data/var/dhcpcd/resolv.conf"
            exit 0
        fi
    done
    echo "QNX target did not answer ssh; see $IMAGE_DIR/output/qemu.out"; exit 1
    ;;
status)
    "${SSH[@]}" uname -a
    ;;
stop)
    sdp
    cd "$IMAGE_DIR" && mkqnximage --stop
    ;;
restart)
    # For a target that stopped answering (run_campaign.py --restart-target). A hung QEMU may ignore
    # mkqnximage --stop, so end this architecture's QEMU process too, then boot again.
    "$0" stop || true
    sleep 5
    pkill -f "qemu-system-${ARCH%le}" 2>/dev/null || true
    sleep 5
    exec "$0" start
    ;;
*)
    sed -n '2,9p' "$0"; exit 1
    ;;
esac
