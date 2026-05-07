pragma circom 2.1.8;

template LocalTrain(n) {
    signal input modelBefore[n];
    signal input gradients[n];
    signal input modelAfter[n];
    signal input learningRate;
    signal output updateHash;
    signal acc[n + 1];

    acc[0] <== 0;
    for (var i = 0; i < n; i++) {
        modelAfter[i] === modelBefore[i] - learningRate * gradients[i];
        acc[i + 1] <== acc[i] + modelAfter[i] * (i + 1);
    }
    updateHash <== acc[n];
}

component main = LocalTrain(10);
