pragma circom 2.1.8;

template Aggregation(clientCount, weightCount) {
    signal input clientWeights[clientCount][weightCount];
    signal input clientSizes[clientCount];
    signal input totalSize;
    signal input averageWeights[weightCount];
    signal output aggregateHash;

    signal weightedSum[weightCount][clientCount + 1];
    signal hashAcc[weightCount + 1];
    hashAcc[0] <== 0;

    for (var j = 0; j < weightCount; j++) {
        weightedSum[j][0] <== 0;
        for (var i = 0; i < clientCount; i++) {
            weightedSum[j][i + 1] <== weightedSum[j][i] + clientWeights[i][j] * clientSizes[i];
        }
        averageWeights[j] * totalSize === weightedSum[j][clientCount];
        hashAcc[j + 1] <== hashAcc[j] + averageWeights[j] * (j + 1);
    }
    aggregateHash <== hashAcc[weightCount];
}

component main = Aggregation(5, 10);
