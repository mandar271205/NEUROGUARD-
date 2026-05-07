# NeuroGuard ZK Circuits

These are small fixed-point Circom scaffolds for the v2 ZK-FL proof path.

- `local_train.circom` proves that a compact set of tracked weights moved according to `modelAfter = modelBefore - learningRate * gradients`.
- `aggregation.circom` proves that the server's compact aggregate equals weighted FedAvg across 5 clients.

They intentionally track only 10 representative weights so local proof generation stays realistic for a project demo. The production path should commit full model tensors with hashes/Merkle roots and prove selected constraints over committed values.

Example workflow:

```powershell
npm install -g snarkjs
circom local_train.circom --r1cs --wasm --sym
snarkjs powersoftau new bn128 12 pot12_0000.ptau -v
snarkjs powersoftau contribute pot12_0000.ptau pot12_0001.ptau --name="ng-demo" -v
snarkjs groth16 setup local_train.r1cs pot12_0001.ptau local_train_0000.zkey
```
