// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract Audit {
    struct AuditEvent {
        bytes32 studentHash;
        bytes32 predictionHash;
        bytes32 zkProofHash;
        uint16 stressScoreBps;
        uint64 timestamp;
    }

    uint16 public immutable alertThresholdBps;
    AuditEvent[] public eventsLog;

    event AuditRecorded(
        uint256 indexed eventId,
        bytes32 indexed studentHash,
        bytes32 predictionHash,
        bytes32 zkProofHash,
        uint16 stressScoreBps
    );

    event Alert(
        uint256 indexed eventId,
        bytes32 indexed studentHash,
        uint16 stressScoreBps
    );

    constructor(uint16 thresholdBps) {
        require(thresholdBps <= 10000, "bad threshold");
        alertThresholdBps = thresholdBps;
    }

    function record(
        bytes32 studentHash,
        bytes32 predictionHash,
        bytes32 zkProofHash,
        uint16 stressScoreBps
    ) external returns (uint256 eventId) {
        require(stressScoreBps <= 10000, "bad score");
        eventId = eventsLog.length;
        eventsLog.push(
            AuditEvent({
                studentHash: studentHash,
                predictionHash: predictionHash,
                zkProofHash: zkProofHash,
                stressScoreBps: stressScoreBps,
                timestamp: uint64(block.timestamp)
            })
        );

        emit AuditRecorded(eventId, studentHash, predictionHash, zkProofHash, stressScoreBps);
        if (stressScoreBps >= alertThresholdBps) {
            emit Alert(eventId, studentHash, stressScoreBps);
        }
    }

    function count() external view returns (uint256) {
        return eventsLog.length;
    }
}
