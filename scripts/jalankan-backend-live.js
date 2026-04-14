const fs = require("fs");
const path = require("path");
const net = require("net");
const readline = require("readline");
const { spawnSync, spawn } = require("child_process");

const akar = process.cwd();
const fileEnv = path.join(akar, ".env");
const argumen = process.argv.slice(2);
const denganDocker = argumen.includes("--dengan-docker");

function bacaArgumenNilai(nama) {
  const indeks = argumen.indexOf(nama);
  if (indeks === -1) {
    return null;
  }
  return argumen[indeks + 1] || null;
}

function bacaEnv() {
  if (!fs.existsSync(fileEnv)) {
    throw new Error("File .env tidak ditemukan.");
  }
  const isi = fs.readFileSync(fileEnv, "utf8");
  const hasil = {};
  for (const baris of isi.split(/\r?\n/)) {
    const trimmed = baris.trim();
    if (!trimmed || trimmed.startsWith("#")) {
      continue;
    }
    const idx = trimmed.indexOf("=");
    if (idx === -1) {
      continue;
    }
    const kunci = trimmed.slice(0, idx).trim();
    const nilai = trimmed.slice(idx + 1).trim();
    hasil[kunci] = nilai;
  }
  return hasil;
}

function cariPython() {
  const kandidat = [
    path.join(akar, ".venv", "Scripts", "python.exe"),
    "python",
    "py",
  ];
  for (const item of kandidat) {
    const hasil = spawnSync(item, ["--version"], {
      cwd: akar,
      stdio: "ignore",
      shell: false,
    });
    if (hasil.status === 0) {
      return item;
    }
  }
  throw new Error("Python tidak ditemukan. Pastikan .venv atau python global tersedia.");
}

function jalankanPerintah(command, args, options = {}) {
  const hasil = spawnSync(command, args, {
    cwd: akar,
    stdio: "inherit",
    shell: false,
    ...options,
  });
  if (hasil.status !== 0) {
    throw new Error(`Perintah gagal: ${command} ${args.join(" ")}`);
  }
}

function jalankanPerintahTangkap(command, args, options = {}) {
  return spawnSync(command, args, {
    cwd: akar,
    stdio: "pipe",
    encoding: "utf8",
    shell: false,
    ...options,
  });
}

function parseKafkaBootstrap(nilai) {
  return nilai
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean)
    .map((item) => {
      const [host, port] = item.split(":");
      return { host, port: Number(port || "9092"), nama: "Kafka" };
    });
}

function parseRedisUrl(nilai) {
  const url = new URL(nilai);
  return { host: url.hostname, port: Number(url.port || "6379"), nama: "Redis" };
}

function parsePostgresDsn(nilai) {
  const url = new URL(nilai);
  return { host: url.hostname, port: Number(url.port || "5432"), nama: "PostgreSQL" };
}

function parseNeo4jUri(nilai) {
  const url = new URL(nilai);
  return { host: url.hostname, port: Number(url.port || "7687"), nama: "Neo4j" };
}

function tungguKoneksi(host, port, nama, timeoutMs = 2000) {
  return new Promise((resolve) => {
    const socket = new net.Socket();
    let selesai = false;

    const akhiri = (ok, pesan) => {
      if (selesai) {
        return;
      }
      selesai = true;
      socket.destroy();
      resolve({ ok, nama, host, port, pesan });
    };

    socket.setTimeout(timeoutMs);
    socket.once("connect", () => akhiri(true, `${nama} terjangkau di ${host}:${port}`));
    socket.once("timeout", () => akhiri(false, `${nama} timeout di ${host}:${port}`));
    socket.once("error", (err) => akhiri(false, `${nama} gagal di ${host}:${port} -> ${err.message}`));
    socket.connect(port, host);
  });
}

async function cekServiceInti(envMap) {
  const target = [
    ...parseKafkaBootstrap(envMap.KAFKA_BOOTSTRAP_SERVERS || ""),
    parseRedisUrl(envMap.REDIS_URL || "redis://localhost:6379/0"),
    parsePostgresDsn(envMap.POSTGRES_DSN || "postgresql://localhost:5432/db"),
    parseNeo4jUri(envMap.NEO4J_URI || "bolt://localhost:7687"),
  ];
  const hasil = [];
  for (const item of target) {
    hasil.push(await tungguKoneksi(item.host, item.port, item.nama));
  }
  return hasil;
}

function outputTangkapKeConsole(hasil) {
  if (hasil.stdout) {
    process.stdout.write(hasil.stdout);
  }
  if (hasil.stderr) {
    process.stderr.write(hasil.stderr);
  }
}

function adaMasalahAutentikasi(outputGabungan) {
  const teks = outputGabungan.toLowerCase();
  return (
    teks.includes("password authentication failed") ||
    teks.includes("authentication failed") ||
    teks.includes("neo.clienterror.security.unauthorized") ||
    teks.includes("the client is unauthorized due to authentication failure")
  );
}

async function tungguServiceSiap(envMap, percobaanMaks = 20, jedaMs = 2000) {
  for (let indeks = 0; indeks < percobaanMaks; indeks += 1) {
    const hasilCek = await cekServiceInti(envMap);
    const gagal = hasilCek.filter((item) => !item.ok);
    if (gagal.length === 0) {
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, jedaMs));
  }
  throw new Error("Service belum siap setelah reset volume.");
}

function resetDockerComposeVolume() {
  console.log("Reset volume Docker backend karena kredensial service tidak sinkron...");
  jalankanPerintah("docker", ["compose", "down", "-v"]);
  jalankanPerintah("docker", ["compose", "up", "-d"]);
}

function prefiksOutput(stream, label, targetStream) {
  if (!stream) {
    return;
  }
  const pembaca = readline.createInterface({ input: stream });
  pembaca.on("line", (baris) => {
    targetStream.write(`[${label}] ${baris}\n`);
  });
}

function buatWorkerLive(label, pythonPath, argsPython) {
  const child = spawn(pythonPath, argsPython, {
    cwd: akar,
    detached: false,
    stdio: ["ignore", "pipe", "pipe"],
    windowsHide: true,
  });

  prefiksOutput(child.stdout, label, process.stdout);
  prefiksOutput(child.stderr, `${label}:ERR`, process.stderr);

  child.on("exit", (kode, sinyal) => {
    const status = kode !== null ? `kode ${kode}` : `sinyal ${sinyal}`;
    process.stdout.write(`[${label}] proses berakhir dengan ${status}\n`);
  });

  return child;
}

function tidur(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function main() {
  const envMap = bacaEnv();
  const pythonPath = cariPython();
  const idBerita = bacaArgumenNilai("--id");
  const limit = bacaArgumenNilai("--limit");

  if (denganDocker) {
    console.log("Menyalakan service infrastruktur via docker compose...");
    jalankanPerintah("docker", ["compose", "up", "-d"]);
  }

  const hasilCek = await cekServiceInti(envMap);
  const gagal = hasilCek.filter((item) => !item.ok);
  if (gagal.length > 0) {
    for (const item of gagal) {
      console.log(`- ${item.pesan}`);
    }
    throw new Error("Dependency inti belum aktif.");
  }

  console.log("Semua service inti terjangkau. Lanjut seed.");
  let hasilSeed = jalankanPerintahTangkap(pythonPath, ["-m", "orchestration.cli", "seed"]);
  if (hasilSeed.status !== 0) {
    outputTangkapKeConsole(hasilSeed);
    const outputGabungan = `${hasilSeed.stdout || ""}\n${hasilSeed.stderr || ""}`;
    if (denganDocker && adaMasalahAutentikasi(outputGabungan)) {
      resetDockerComposeVolume();
      await tungguServiceSiap(envMap);
      hasilSeed = jalankanPerintahTangkap(pythonPath, ["-m", "orchestration.cli", "seed"]);
      if (hasilSeed.status !== 0) {
        outputTangkapKeConsole(hasilSeed);
        throw new Error(`Perintah gagal: ${pythonPath} -m orchestration.cli seed`);
      }
    } else {
      throw new Error(`Perintah gagal: ${pythonPath} -m orchestration.cli seed`);
    }
  }
  outputTangkapKeConsole(hasilSeed);

  console.log("Menyalakan worker live TIA, NAA, dan PTA...");
  const workers = [
    buatWorkerLive("TIA", pythonPath, ["-m", "orchestration.cli", "run-tia"]),
    buatWorkerLive("NAA", pythonPath, ["-m", "orchestration.cli", "run-naa"]),
    buatWorkerLive("PTA", pythonPath, ["-m", "orchestration.cli", "run-pta-worker"]),
  ];

  const hentikanSemua = () => {
    for (const worker of workers) {
      if (worker && !worker.killed) {
        try {
          worker.kill();
        } catch (err) {
          // abaikan
        }
      }
    }
  };

  process.on("SIGINT", () => {
    console.log("\nMenghentikan worker live...");
    hentikanSemua();
    process.exit(0);
  });

  process.on("SIGTERM", () => {
    hentikanSemua();
    process.exit(0);
  });

  await tidur(5000);

  console.log("Worker live sudah menyala. Menerbitkan OSINT...");
  const argsPublish = ["-m", "orchestration.cli", "publish-osint"];
  if (idBerita) {
    argsPublish.push("--id", idBerita);
  }
  if (limit) {
    argsPublish.push("--limit", limit);
  }
  jalankanPerintah(pythonPath, argsPublish);

  console.log("Backend live aktif. Tekan Ctrl+C untuk berhenti.");

  await new Promise(() => {});
}

main().catch((err) => {
  console.error(err.message);
  process.exit(1);
});
