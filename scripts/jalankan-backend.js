const fs = require("fs");
const path = require("path");
const net = require("net");
const { spawnSync, spawn } = require("child_process");

const akar = process.cwd();
const direktoriLogs = path.join(akar, "logs");
const direktoriState = path.join(akar, "runtime_state");
const fileState = path.join(direktoriState, "backend-processes.json");
const fileEnv = path.join(akar, ".env");
const argumen = new Set(process.argv.slice(2));
const denganDocker = argumen.has("--dengan-docker");
const statusSaja = argumen.has("--status-saja");

function pastikanDirektori(jalur) {
  if (!fs.existsSync(jalur)) {
    fs.mkdirSync(jalur, { recursive: true });
  }
}

function bacaState() {
  if (!fs.existsSync(fileState)) {
    return null;
  }
  return JSON.parse(fs.readFileSync(fileState, "utf8"));
}

function simpanState(payload) {
  pastikanDirektori(direktoriState);
  fs.writeFileSync(fileState, JSON.stringify(payload, null, 2));
}

function jalankanPerintah(command, args, options = {}) {
  const hasil = spawnSync(command, args, {
    cwd: akar,
    stdio: "inherit",
    shell: false,
    ...options
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
    ...options
  });
}

function cariPython() {
  const kandidat = [
    path.join(akar, ".venv", "Scripts", "python.exe"),
    "python",
    "py"
  ];
  for (const item of kandidat) {
    const hasil = spawnSync(item, ["--version"], {
      cwd: akar,
      stdio: "ignore",
      shell: false
    });
    if (hasil.status === 0) {
      return item;
    }
  }
  throw new Error("Python tidak ditemukan. Pastikan .venv atau python global tersedia.");
}

function cekNpmStatus() {
  const state = bacaState();
  if (!state) {
    console.log("Belum ada backend yang didaftarkan.");
    return;
  }
  console.log("Status backend terakhir:");
  console.log(JSON.stringify(state, null, 2));
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
    const key = trimmed.slice(0, idx).trim();
    const value = trimmed.slice(idx + 1).trim();
    hasil[key] = value;
  }
  return hasil;
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

function parseKafkaBootstrap(value) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean)
    .map((item) => {
      const [host, port] = item.split(":");
      return { host, port: Number(port || "9092"), nama: "Kafka" };
    });
}

function parseRedisUrl(value) {
  const url = new URL(value);
  return { host: url.hostname, port: Number(url.port || "6379"), nama: "Redis" };
}

function parsePostgresDsn(value) {
  const url = new URL(value);
  return { host: url.hostname, port: Number(url.port || "5432"), nama: "PostgreSQL" };
}

function parseNeo4jUri(value) {
  const url = new URL(value);
  return { host: url.hostname, port: Number(url.port || "7687"), nama: "Neo4j" };
}

async function cekServiceInti(envMap) {
  const targets = [
    ...parseKafkaBootstrap(envMap.KAFKA_BOOTSTRAP_SERVERS || ""),
    parseRedisUrl(envMap.REDIS_URL || "redis://localhost:6379/0"),
    parsePostgresDsn(envMap.POSTGRES_DSN || "postgresql://localhost:5432/db"),
    parseNeo4jUri(envMap.NEO4J_URI || "bolt://localhost:7687")
  ];

  const hasil = [];
  for (const target of targets) {
    hasil.push(await tungguKoneksi(target.host, target.port, target.nama));
  }
  return hasil;
}

function jalankanDockerCompose() {
  console.log("Menyalakan service infrastruktur via docker compose...");
  try {
    jalankanPerintah("docker", ["compose", "up", "-d"]);
  } catch (err) {
    throw new Error(
      "Docker tidak bisa dipakai saat ini. Jalankan service secara manual lalu pakai `npm run back`, atau hidupkan Docker Desktop lalu ulangi dengan `npm run back:docker`."
    );
  }
}

function resetDockerComposeVolume() {
  console.log("Reset volume Docker backend karena kredensial service tidak sinkron...");
  jalankanPerintah("docker", ["compose", "down", "-v"]);
  jalankanPerintah("docker", ["compose", "up", "-d"]);
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
  throw new Error("Service Docker belum siap setelah reset volume.");
}

async function jalankanSeedDanPublish(pythonPath, envMap) {
  console.log("Menjalankan seed PostgreSQL dan Neo4j...");
  let hasilSeed = jalankanPerintahTangkap(pythonPath, ["-m", "orchestration.cli", "seed"]);
  if (hasilSeed.status !== 0) {
    outputTangkapKeConsole(hasilSeed);
    const outputGabungan = `${hasilSeed.stdout || ""}\n${hasilSeed.stderr || ""}`;
    if (denganDocker && adaMasalahAutentikasi(outputGabungan)) {
      console.log("Terdeteksi drift kredensial pada volume Docker. Akan dilakukan reset data uji lalu seed diulang.");
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
  } else {
    outputTangkapKeConsole(hasilSeed);
  }
  console.log("Menerbitkan data OSINT ke Kafka...");
  jalankanPerintah(pythonPath, ["-m", "orchestration.cli", "publish-osint"]);
}

function spawnWorker(nama, pythonPath, argsPython) {
  pastikanDirektori(direktoriLogs);
  const logOutput = fs.openSync(path.join(direktoriLogs, `${nama}.log`), "w");
  const logError = fs.openSync(path.join(direktoriLogs, `${nama}.err.log`), "w");
  const child = spawn(pythonPath, argsPython, {
    cwd: akar,
    detached: true,
    stdio: ["ignore", logOutput, logError],
    windowsHide: true
  });
  child.unref();
  return {
    nama,
    pid: child.pid,
    perintah: [pythonPath, ...argsPython].join(" "),
    log: path.relative(akar, path.join(direktoriLogs, `${nama}.log`)),
    error_log: path.relative(akar, path.join(direktoriLogs, `${nama}.err.log`))
  };
}

function tidur(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function prosesMasihHidup(pid) {
  try {
    process.kill(pid, 0);
    return true;
  } catch (err) {
    return false;
  }
}

async function validasiWorkerAwal(prosesList) {
  await tidur(4000);
  const mati = prosesList.filter((item) => !prosesMasihHidup(item.pid));
  if (mati.length > 0) {
    const daftar = mati.map((item) => `${item.nama} (lihat ${item.error_log})`).join(", ");
    throw new Error(`Sebagian worker mati setelah start awal: ${daftar}`);
  }
}

async function main() {
  if (statusSaja) {
    cekNpmStatus();
    return;
  }

  const envMap = bacaEnv();
  const pythonPath = cariPython();

  if (denganDocker) {
    jalankanDockerCompose();
  } else {
    console.log("Mode default tanpa Docker aktif.");
  }

  const hasilCek = await cekServiceInti(envMap);
  const gagal = hasilCek.filter((item) => !item.ok);
  if (gagal.length > 0) {
    console.log("Service yang belum siap:");
    for (const item of gagal) {
      console.log(`- ${item.pesan}`);
    }
    throw new Error(
      "Backend tidak dijalankan karena dependency inti belum aktif. Nyalakan service manual, atau gunakan `npm run back:docker` jika Docker Desktop tersedia."
    );
  }

  console.log("Semua service inti terjangkau. Lanjut seed.");
  console.log("Menjalankan seed PostgreSQL dan Neo4j...");
  let hasilSeed = jalankanPerintahTangkap(pythonPath, ["-m", "orchestration.cli", "seed"]);
  if (hasilSeed.status !== 0) {
    outputTangkapKeConsole(hasilSeed);
    const outputGabungan = `${hasilSeed.stdout || ""}\n${hasilSeed.stderr || ""}`;
    if (denganDocker && adaMasalahAutentikasi(outputGabungan)) {
      console.log("Terdeteksi drift kredensial pada volume Docker. Akan dilakukan reset data uji lalu seed diulang.");
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
  } else {
    outputTangkapKeConsole(hasilSeed);
  }

  console.log("Menyalakan worker TIA, NAA, dan PTA...");
  const proses = [
    spawnWorker("tia", pythonPath, ["-m", "orchestration.cli", "run-tia"]),
    spawnWorker("naa", pythonPath, ["-m", "orchestration.cli", "run-naa"]),
    spawnWorker("pta", pythonPath, ["-m", "orchestration.cli", "run-pta-worker"])
  ];
  await validasiWorkerAwal(proses);

  console.log("Worker hidup. Menerbitkan data OSINT ke Kafka...");
  jalankanPerintah(pythonPath, ["-m", "orchestration.cli", "publish-osint"]);

  const state = {
    dibuat_pada: new Date().toISOString(),
    dengan_docker: denganDocker,
    proses
  };
  simpanState(state);

  console.log("Backend aktif. Detail proses:");
  console.log(JSON.stringify(state, null, 2));
  console.log("Log tersedia di folder logs/.");
}

main().catch((err) => {
  console.error(err.message);
  process.exit(1);
});
