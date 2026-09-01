// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title ContentRegistry
/// @author Built from scratch for Face → Web → Blockchain pipeline
/// @notice Minimal fingerprint registry for Polygon Amoy testnet.
///         Stores only SHA-256(bytes32) — no images, no PII, cheap to call.
///         Designed for HH GOA 2026 demo: register → verify → tamper demo.
contract ContentRegistry {
    struct Record {
        bytes32 contentHash;
        address registrant;
        uint256 timestamp;
        uint256 blockNumber;
        bool exists;
    }

    mapping(bytes32 => Record) private records;
    uint256 public totalRecords;

    event ContentRegistered(
        bytes32 indexed contentHash,
        address indexed registrant,
        uint256 timestamp,
        uint256 blockNumber
    );

    /// @notice Register a new content fingerprint.
    /// @param contentHash SHA-256 digest as bytes32 (0x…)
    function register(bytes32 contentHash) external {
        require(contentHash != bytes32(0), "empty hash");
        require(!records[contentHash].exists, "already registered");

        records[contentHash] = Record({
            contentHash: contentHash,
            registrant: msg.sender,
            timestamp: block.timestamp,
            blockNumber: block.number,
            exists: true
        });

        totalRecords += 1;

        emit ContentRegistered(contentHash, msg.sender, block.timestamp, block.number);
    }

    /// @notice Retrieve full record for a hash.
    function getRecord(bytes32 contentHash)
        external
        view
        returns (
            bytes32 hash_,
            address registrant,
            uint256 timestamp,
            uint256 blockNumber,
            bool exists
        )
    {
        Record storage r = records[contentHash];
        return (r.contentHash, r.registrant, r.timestamp, r.blockNumber, r.exists);
    }

    /// @notice Check whether a hash is registered.
    function verify(bytes32 contentHash) external view returns (bool) {
        return records[contentHash].exists;
    }
}
