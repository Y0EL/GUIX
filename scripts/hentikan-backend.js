const fs = require("fs");
const path = require("path");
const { spawnSync } = require("child_process");

const akar = process.cwd();
const fileState = path.join(akar, "runtime_state", "backend-processes.json");

function bacaState() {
  if (!fs.existsSync(fileState)) {
    return null;
  }
  return JSON.parse(fs.readFileSync(fileState, "utf8"));
}

function hentikanPid(pid) {
  const hasil = spawnSync("taskkill", ["/PID", String(pid), "/T", "/F"], {
    cwd: akar,
    stdio: "inherit",
    shell: false
  });
  return hasil.status === 0;
}

function main() {
  const state = bacaState();
  if (!state || !Array.isArray(state.proses)) {
    console.log("Tidak ada proses backend yang tercatat.");
    return;
  }

  for (const proses of state.proses) {
    if (proses && proses.pid) {
      console.log(`Menghentikan ${proses.nama} (PID ${proses.pid})...`);
      hentikanPid(proses.pid);
    }
  }

  fs.unlinkSync(fileState);
  console.log("Semua proses backend yang tercatat sudah dihentikan.");
}

main();
