// Exercises the parts of std a ported crate leans on: threads, sync, fs, time, net, process, env.
use std::io::{Read, Write};
use std::sync::{mpsc, Arc, Mutex};
use std::{fs, net, process, thread, time};

fn check(name: &str, ok: bool, ok_count: &mut u32, total: &mut u32) {
    *total += 1;
    if ok { *ok_count += 1; }
    println!("{} {}", if ok { "PASS" } else { "FAIL" }, name);
}

fn main() {
    let (mut ok, mut total) = (0, 0);
    let counter = Arc::new(Mutex::new(0));
    let hs: Vec<_> = (0..4).map(|_| { let c = counter.clone(); thread::spawn(move || { for _ in 0..1000 { *c.lock().unwrap() += 1; } }) }).collect();
    for h in hs { h.join().unwrap(); }
    check("threads + mutex", *counter.lock().unwrap() == 4000, &mut ok, &mut total);

    let (tx, rx) = mpsc::channel();
    thread::spawn(move || tx.send(42).unwrap());
    check("mpsc channel", rx.recv().unwrap() == 42, &mut ok, &mut total);

    let p = std::env::temp_dir().join("rustgate.txt");
    let fs_ok = fs::write(&p, b"qnx").is_ok() && fs::read(&p).map(|b| b == b"qnx").unwrap_or(false)
        && fs::metadata(&p).map(|m| m.len() == 3).unwrap_or(false) && fs::remove_file(&p).is_ok();
    check(&format!("fs write/read/metadata/remove in {}", std::env::temp_dir().display()), fs_ok, &mut ok, &mut total);

    let d = std::env::temp_dir().join("rustgate-dir");
    let dir_ok = fs::create_dir_all(d.join("a/b")).is_ok() && fs::read_dir(&d).map(|r| r.count() == 1).unwrap_or(false)
        && fs::remove_dir_all(&d).is_ok();
    check("fs create_dir_all/read_dir/remove_dir_all", dir_ok, &mut ok, &mut total);

    let t0 = time::Instant::now();
    thread::sleep(time::Duration::from_millis(50));
    let el = t0.elapsed();
    check(&format!("Instant + sleep(50ms) -> {:?}", el), el >= time::Duration::from_millis(50), &mut ok, &mut total);
    check("SystemTime after 2020", time::SystemTime::now().duration_since(time::UNIX_EPOCH).unwrap().as_secs() > 1_577_836_800, &mut ok, &mut total);

    let net_ok = (|| -> std::io::Result<bool> {
        let l = net::TcpListener::bind("127.0.0.1:0")?;
        let addr = l.local_addr()?;
        let h = thread::spawn(move || { let (mut s, _) = l.accept().unwrap(); let mut b = [0u8; 4]; s.read_exact(&mut b).unwrap(); s.write_all(&b).unwrap(); });
        let mut c = net::TcpStream::connect(addr)?;
        c.write_all(b"ping")?;
        let mut b = [0u8; 4];
        c.read_exact(&mut b)?;
        h.join().unwrap();
        Ok(&b == b"ping")
    })().unwrap_or_else(|e| { println!("  net error: {e}"); false });
    check("TCP loopback echo", net_ok, &mut ok, &mut total);

    let udp_ok = (|| -> std::io::Result<bool> {
        let a = net::UdpSocket::bind("127.0.0.1:0")?;
        let b = net::UdpSocket::bind("127.0.0.1:0")?;
        a.send_to(b"u", b.local_addr()?)?;
        let mut buf = [0u8; 1];
        Ok(b.recv_from(&mut buf)?.0 == 1)
    })().unwrap_or_else(|e| { println!("  udp error: {e}"); false });
    check("UDP loopback", udp_ok, &mut ok, &mut total);

    let out = process::Command::new("uname").arg("-s").output();
    let uname = out.as_ref().map(|o| String::from_utf8_lossy(&o.stdout).trim().to_string()).unwrap_or_default();
    check(&format!("process::Command uname -s -> {uname:?}"), out.map(|o| o.status.success()).unwrap_or(false), &mut ok, &mut total);

    std::env::set_var("RUSTGATE", "1");
    check("env var", std::env::var("RUSTGATE").as_deref() == Ok("1"), &mut ok, &mut total);
    check(&format!("available_parallelism -> {:?}", thread::available_parallelism().map(|n| n.get())), thread::available_parallelism().is_ok(), &mut ok, &mut total);

    let r = std::panic::catch_unwind(|| panic!("unwind"));
    check("panic unwinds and is caught", r.is_err(), &mut ok, &mut total);

    println!("{ok}/{total} std checks passed on {} {}", std::env::consts::OS, std::env::consts::ARCH);
    process::exit(if ok == total { 0 } else { 1 });
}
