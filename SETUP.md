# Setup: QNX SDP 8.0, the QEMU target, and qnx-porter

qnx-porter runs on a **Linux host** (Ubuntu 22.04 or 24.04, or WSL2 Ubuntu on Windows 11). QNX's own
`mkqnximage` tool runs QEMU targets only on Ubuntu hosts, so on Windows we use WSL2 for everything.

Total time: about 45 minutes, most of it downloads. Steps marked **(you)** need your own account and
cannot be scripted. Never put your QNX password or licence key in this repository or in a chat.

## 1. QNX Everywhere account and free licence (you)
1. Open https://qnx.software/en/developers/get-started/qnx-everywhere and choose **Get QNX Everywhere**.
2. Create a myQNX account (or sign in), then request the **free non-commercial licence** for
   QNX SDP 8.0. It arrives in your myQNX account under *Licenses* within minutes.

## 2. WSL2 Ubuntu (Windows only)
In PowerShell: `wsl --install -d Ubuntu-22.04`, reboot if asked, then open the **Ubuntu** terminal.
Every command below runs in that Ubuntu terminal.

```bash
sudo apt update && sudo apt install -y build-essential cmake ninja-build meson autoconf automake libtool \
  pkg-config git python3 python3-pip qemu-system-x86 qemu-utils bridge-utils net-tools openssh-client
```

## 3. QNX Software Center and SDP 8.0 (you)
1. From the QNX Everywhere page, download **QNX Software Center for Linux hosts**
   (`qnx-setup-*-linux.run`) and run it: `chmod +x qnx-setup-*.run && ./qnx-setup-*.run`.
   On WSL the installer window opens through WSLg; if it doesn't, run `./qnx-setup-*.run --help` for
   the console mode.
2. Start the Software Center (`~/qnx/qnxsoftwarecenter/qnxsoftwarecenter`), sign in with your myQNX
   account, and add the licence from step 1.
3. Choose **Add Installation → QNX Software Development Platform 8.0** and install it to the default
   path **`~/qnx800`**.
4. Check:
   ```bash
   source ~/qnx800/qnxsdp-env.sh
   qcc -V            # lists gcc_ntox86_64 and gcc_ntoaarch64le
   ```

## 4. QEMU x86_64 target running QNX 8.0
```bash
source ~/qnx800/qnxsdp-env.sh
ssh-keygen -t ed25519 -N "" -f ~/.ssh/id_ed25519   # skip if you already have a key
mkdir -p ~/qnx-images/qemu && cd ~/qnx-images/qemu
mkqnximage --type=qemu --arch=x86_64 --ip=172.31.1.11 \
  --ssh-ident=$HOME/.ssh/id_ed25519.pub --data-size=5000 --data-inodes=40000
mkqnximage --run=-h        # starts QEMU in the background (headless)
ssh root@172.31.1.11 uname -a   # expect: QNX ... 8.0.0 ... x86_64
```
- `mkqnximage --stop` stops it; `mkqnximage --help=brief` lists every option.
- `/data` is the image's large writable partition; qnx-porter copies test trees to `/data/qnx-porter`.
- If `--run` complains about networking, it needs a bridge; it prints the `sudo .../net.sh` command to
  run once.

## 5. qnx-porter
```bash
git clone https://github.com/thegoodengineers/qnx-porter && cd qnx-porter
python3 -m pip install -e ".[test]"
python3 -m pytest -q                 # 34 tests, no QNX needed
source ~/qnx800/qnxsdp-env.sh
qnx-porter doctor                    # every line should say ok
qnx-porter port https://github.com/json-c/json-c.git --tag json-c-0.18-20240915 --target root@172.31.1.11
python3 scripts/ports_csv.py         # results/ports.csv from ports/*/report.json
```

## 6. Optional: the model for the long tail
Deterministic rules run first and need nothing. For errors no rule handles, set (in your shell only,
never in a file in this repository):
```bash
export QNX_PORTER_API_KEY="..."      # key for any OpenAI-compatible chat-completions endpoint
export QNX_PORTER_MODEL="..."        # model ID from that provider's model list
export QNX_PORTER_BASE_URL="..."     # optional; default https://api.openai.com/v1
```
`--no-model` turns it off for a run.

## Things to check on the first real install
These are written from QNX's documentation, not yet run on our machine:
- the SDP 8.0 GNU-style drivers are named `x86_64-pc-nto-qnx8.0.0-gcc` etc. (`qnx-porter doctor` checks it);
- the QEMU image's sshd accepts `root` with the key from `--ssh-ident`;
- the image has `tar` (qnx-porter copies test trees with `tar` over ssh).
If one is wrong, note it in `docs/LEARNINGS.md` and fix `qnx_porter/qnx.py` or `qnx_porter/target.py`.
