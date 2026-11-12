// 화면의 모듈들이 서로 맞물리는지 본다.
// 진입 파일에서 시작해 import를 따라가며 없는 파일과 없는 export를 찾는다. 코드를 실행하지는 않는다.
// 운영 콘솔은 공개 사이트의 화면 도우미를 복사해 쓰므로, 사이트 쪽에서 함수 하나를 빼면 콘솔이 통째로 열리지 않게 된다.
// 그런 일을 올리기 전에 잡으려는 것이다(tests/test_console.py가 부른다).
// 쓰는 법: node --experimental-vm-modules tools/dev/modlink.mjs <진입 파일>
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";

const entry = path.resolve(process.argv[2] || "");
const context = vm.createContext({});
const modules = new Map();

function load(file) {
  if (!modules.has(file)) {
    modules.set(file, new vm.SourceTextModule(fs.readFileSync(file, "utf8"), { identifier: file, context }));
  }
  return modules.get(file);
}

function linker(specifier, referencing) {
  if (!specifier.startsWith(".")) throw new Error(`저장소 밖의 모듈을 부름: ${specifier} (${path.basename(referencing.identifier)})`);
  const target = path.resolve(path.dirname(referencing.identifier), specifier);
  if (!fs.existsSync(target)) throw new Error(`없는 파일을 부름: ${specifier} (${path.basename(referencing.identifier)})`);
  return load(target);
}

try {
  await load(entry).link(linker);
  console.log(`맞물림: 모듈 ${modules.size}개`);
} catch (error) {
  console.log(`문제: ${error.message}`);
  process.exit(1);
}
