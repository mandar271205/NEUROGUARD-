# NeuroGuard Federated Learning

This folder contains the v2 FL starting point. It keeps raw student audio local, trains a small head on synthetic/client-local features, and sends only compact weight updates plus proof inputs.

Run the NumPy-only simulation:

```powershell
python fl/simulate_fedavg.py
```

Install Flower later when you are ready to replace the simulated clients with real `flwr.client.NumPyClient` instances:

```powershell
pip install flwr torch torchaudio transformers
```
