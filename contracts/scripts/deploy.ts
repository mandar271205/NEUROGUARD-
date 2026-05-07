import { ethers } from "hardhat";

async function main() {
  const consent = await ethers.deployContract("ConsentDAO");
  await consent.waitForDeployment();

  const audit = await ethers.deployContract("Audit", [7000]);
  await audit.waitForDeployment();

  console.log("ConsentDAO:", await consent.getAddress());
  console.log("Audit:", await audit.getAddress());
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
