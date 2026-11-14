import subprocess
import time

from qnx_porter import hang
from qnx_porter.target import Target, remote_command

# traceprinter lines as the SDP's traceprinter prints them (format checked on a 1 s trace from the x86_64 target)
TRACE = """\
t:0x1 CPU:00 THREAD          :THRUNNING          pid:500 tid:2
t:0x2 CPU:00 KER_CALL        :MSG_READV/16       coid:0x4
t:0x3 CPU:00 KER_CALL        :MSG_READV/16       coid:0x4
t:0x4 CPU:01 THREAD          :THRUNNING          pid:1 tid:5
t:0x5 CPU:01 KER_CALL        :SYNC_SEM_WAIT/85   sync_p:0x1
t:0x6 CPU:00 KER_CALL        :CONNECT_FLAGS/34   coid:0x4
t:0x7 CPU:00 THREAD          :THRUNNING          pid:500 tid:2
"""


def test_summary_counts_kernel_calls_of_the_running_thread_only():
    s = hang.summary(TRACE, {500, 501})
    assert "pid 500 tid 2: ran 2 time(s), 3 kernel call(s) (MSG_READV x2, CONNECT_FLAGS x1)" in s
    assert "SYNC_SEM_WAIT" not in s  # pid 1's call, on another CPU
    assert "pid(s) 501: no thread ran during the trace" in s
    assert "all waiting" in hang.summary(TRACE, {777})


def test_snapshot_pids_reads_pidin_lines():
    out = "test output\n" + hang.MARK + ", 52 s after the start\n     pid tid name\n 4100 1 nng_test 10r CONDVAR\n 4100 2 nng_test 10r READY\n"
    assert hang.snapshot_pids(out) == {4100}


def test_watcher_snapshots_a_stuck_test_and_leaves_a_finished_one_alone(tmp_path, monkeypatch):
    # Runs the generated shell on the host: `pidin` and `tracelogger` do not exist here, so the snapshot holds
    # their "not found" lines, which is enough to see that it was taken (or not) and printed.
    monkeypatch.setattr(hang, "MIN_LIMIT", 1)
    monkeypatch.setattr(hang, "LEAD", 1)
    t = Target("unused", 22, str(tmp_path / "root"))
    diag = str(tmp_path / "hang-0")

    def run(argv, limit):
        cmd = remote_command(t, str(tmp_path), str(tmp_path), argv, same_path=True, limit=limit, diag=diag)
        start = time.time()
        r = subprocess.run(["sh", "-c", cmd], capture_output=True, text=True, timeout=30)
        return r.returncode, r.stdout, time.time() - start

    rc, out, took = run(["true"], 3)
    assert rc == 0 and hang.MARK not in out and took < 2  # not held open by the sleeping watcher
    rc, out, took = run(["sleep", "20"], 3)
    assert rc == 137 and hang.MARK in out and took < 10


def test_read_trace_drops_raw_trace_unless_kept(tmp_path, monkeypatch):
    monkeypatch.setenv("QNX_HOST", str(tmp_path / "no-sdp"))
    kept, dropped = tmp_path / "hang-1.kev", tmp_path / "hang-4.kev"
    assert hang.read_trace(b"kev", kept) == ""
    assert hang.read_trace(b"kev", dropped, keep=False) == ""
    assert kept.read_bytes() == b"kev" and not dropped.exists()
