// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract ConsentDAO {
    struct Consent {
        bool dataCollection;
        bool mlProcessing;
        bool zkFL;
        bool rawAudioStorage;
        uint64 expiresAt;
        uint64 updatedAt;
    }

    mapping(bytes32 => Consent) public consents;

    event ConsentUpdated(
        bytes32 indexed studentHash,
        bool dataCollection,
        bool mlProcessing,
        bool zkFL,
        bool rawAudioStorage,
        uint64 expiresAt
    );

    function setConsent(
        bytes32 studentHash,
        bool dataCollection,
        bool mlProcessing,
        bool zkFL,
        bool rawAudioStorage,
        uint64 expiresAt
    ) external {
        consents[studentHash] = Consent({
            dataCollection: dataCollection,
            mlProcessing: mlProcessing,
            zkFL: zkFL,
            rawAudioStorage: rawAudioStorage,
            expiresAt: expiresAt,
            updatedAt: uint64(block.timestamp)
        });

        emit ConsentUpdated(studentHash, dataCollection, mlProcessing, zkFL, rawAudioStorage, expiresAt);
    }

    function isActive(bytes32 studentHash) external view returns (bool) {
        Consent memory consent = consents[studentHash];
        if (!consent.dataCollection || !consent.mlProcessing) return false;
        return consent.expiresAt == 0 || consent.expiresAt >= block.timestamp;
    }
}
