-- =============================================================================
-- Card Payments Schema for CDC Benchmarking
-- SQL Server 2022
--
-- NOTE: In production, PAN must be encrypted (TDE / column-level encryption /
--       tokenization). Raw PANs here are intentional TEST DATA ONLY.
--       Never store raw PANs in a production system (PCI DSS Req 3.3).
-- =============================================================================

USE CDC_BENCHMARK_DB;
GO

-- ---------------------------------------------------------------------------
-- Reference: Card Networks
-- ---------------------------------------------------------------------------
CREATE TABLE dbo.card_network (
    network_id      TINYINT         NOT NULL PRIMARY KEY,
    network_code    VARCHAR(10)     NOT NULL,   -- VISA, MC, AMEX, DISC
    network_name    VARCHAR(50)     NOT NULL,
    pan_length      TINYINT         NOT NULL,   -- 15 or 16
    CONSTRAINT uq_card_network_code UNIQUE (network_code)
);

INSERT INTO dbo.card_network VALUES
(1, 'VISA',  'Visa',       16),
(2, 'MC',    'Mastercard', 16),
(3, 'AMEX',  'Amex',       15),
(4, 'DISC',  'Discover',   16);
GO

-- ---------------------------------------------------------------------------
-- Reference: Merchant Category Codes (subset)
-- ---------------------------------------------------------------------------
CREATE TABLE dbo.merchant_category (
    mcc             SMALLINT        NOT NULL PRIMARY KEY,
    description     VARCHAR(100)    NOT NULL
);

INSERT INTO dbo.merchant_category VALUES
(5411, 'Grocery Stores, Supermarkets'),
(5912, 'Drug Stores and Pharmacies'),
(5541, 'Service Stations'),
(5812, 'Eating Places, Restaurants'),
(5999, 'Miscellaneous and Specialty Retail'),
(4111, 'Local and Suburban Commuter Passenger Transport'),
(7011, 'Hotels, Motels, and Resorts'),
(4816, 'Computer Network/Information Services'),
(5045, 'Computers, Peripherals, and Software'),
(6011, 'Automated Cash Disbursements'),
(5310, 'Discount Stores'),
(5651, 'Family Clothing Stores'),
(5732, 'Electronics Stores'),
(4121, 'Taxicabs and Limousines'),
(7941, 'Professional Sports Clubs');
GO

-- ---------------------------------------------------------------------------
-- Reference: Response Codes
-- ---------------------------------------------------------------------------
CREATE TABLE dbo.response_code (
    response_code   CHAR(2)         NOT NULL PRIMARY KEY,
    description     VARCHAR(100)    NOT NULL,
    is_approval     BIT             NOT NULL
);

INSERT INTO dbo.response_code VALUES
('00', 'Approved',                              1),
('01', 'Refer to Card Issuer',                  0),
('05', 'Do Not Honor',                          0),
('12', 'Invalid Transaction',                   0),
('14', 'Invalid Card Number',                   0),
('51', 'Insufficient Funds',                    0),
('54', 'Expired Card',                          0),
('57', 'Transaction Not Permitted to Card',     0),
('61', 'Exceeds Withdrawal Amount Limit',       0),
('65', 'Exceeds Withdrawal Frequency Limit',    0),
('75', 'Allowable PIN Tries Exceeded',          0),
('91', 'Issuer Unavailable',                    0),
('96', 'System Error',                          0);
GO

-- ---------------------------------------------------------------------------
-- Core: card_transaction
-- This is the hot table that CDC will capture changes on.
-- ---------------------------------------------------------------------------
CREATE TABLE dbo.card_transaction (
    -- Surrogate key
    txn_id                  BIGINT          NOT NULL IDENTITY(1,1),

    -- Card identifiers
    -- *** TEST DATA ONLY — encrypt in production (PCI DSS Req 3.3) ***
    pan                     VARCHAR(19)     NOT NULL,   -- full PAN, unmasked
    pan_masked              VARCHAR(19)     NOT NULL,   -- first6****last4
    pan_token               VARCHAR(64)     NOT NULL,   -- simulated network token
    network_id              TINYINT         NOT NULL,
    card_type               VARCHAR(10)     NOT NULL,   -- CREDIT / DEBIT / PREPAID
    expiry_month            TINYINT         NOT NULL,   -- 1-12
    expiry_year             SMALLINT        NOT NULL,   -- 4-digit
    cardholder_name         VARCHAR(100)    NOT NULL,

    -- Transaction identifiers
    retrieval_ref_num       CHAR(12)        NOT NULL,   -- RRN
    system_trace_audit_num  CHAR(6)         NOT NULL,   -- STAN
    auth_code               CHAR(6)         NULL,       -- populated on approval

    -- Merchant
    merchant_id             VARCHAR(15)     NOT NULL,
    merchant_name           VARCHAR(100)    NOT NULL,
    merchant_city           VARCHAR(50)     NOT NULL,
    merchant_state          CHAR(2)         NOT NULL,
    merchant_country        CHAR(3)         NOT NULL,   -- ISO 3166-1 alpha-3
    mcc                     SMALLINT        NOT NULL,
    terminal_id             VARCHAR(8)      NOT NULL,
    acquirer_bin            CHAR(6)         NOT NULL,

    -- Transaction details
    txn_type                VARCHAR(20)     NOT NULL,   -- PURCHASE / REFUND / VOID / AUTH_ONLY / CAPTURE
    entry_mode              VARCHAR(20)     NOT NULL,   -- CHIP / SWIPE / CONTACTLESS / MANUAL / ECOMMERCE
    txn_amount              DECIMAL(12,2)   NOT NULL,
    currency_code           CHAR(3)         NOT NULL,   -- ISO 4217
    txn_currency_amount     DECIMAL(12,2)   NOT NULL,   -- amount in txn currency (if different)
    exchange_rate           DECIMAL(10,6)   NOT NULL DEFAULT 1.0,

    -- Authorization / settlement
    response_code           CHAR(2)         NOT NULL,
    txn_status              VARCHAR(20)     NOT NULL,   -- APPROVED / DECLINED / PENDING / REVERSED / SETTLED
    is_partial_approval     BIT             NOT NULL DEFAULT 0,
    approved_amount         DECIMAL(12,2)   NULL,

    -- Risk
    cvv_result              CHAR(1)         NULL,       -- M=match, N=no match, P=not processed, U=issuer not certified
    avs_result              CHAR(1)         NULL,       -- Y/N/A/Z/S/U/R
    is_3ds                  BIT             NOT NULL DEFAULT 0,
    is_fraud_flag           BIT             NOT NULL DEFAULT 0,
    fraud_score             DECIMAL(5,4)    NULL,       -- 0.0000 - 1.0000

    -- Timestamps (all UTC)
    txn_timestamp           DATETIME2(3)    NOT NULL,
    auth_timestamp          DATETIME2(3)    NULL,
    settlement_timestamp    DATETIME2(3)    NULL,
    created_at              DATETIME2(3)    NOT NULL DEFAULT SYSUTCDATETIME(),
    updated_at              DATETIME2(3)    NOT NULL DEFAULT SYSUTCDATETIME(),

    -- Reversal linkage
    original_txn_id         BIGINT          NULL,       -- FK back to self for reversals

    CONSTRAINT pk_card_transaction PRIMARY KEY CLUSTERED (txn_id),
    CONSTRAINT fk_card_txn_network FOREIGN KEY (network_id) REFERENCES dbo.card_network(network_id),
    CONSTRAINT fk_card_txn_mcc     FOREIGN KEY (mcc)        REFERENCES dbo.merchant_category(mcc),
    CONSTRAINT chk_txn_type   CHECK (txn_type   IN ('PURCHASE','REFUND','VOID','AUTH_ONLY','CAPTURE')),
    CONSTRAINT chk_entry_mode CHECK (entry_mode IN ('CHIP','SWIPE','CONTACTLESS','MANUAL','ECOMMERCE')),
    CONSTRAINT chk_txn_status CHECK (txn_status IN ('APPROVED','DECLINED','PENDING','REVERSED','SETTLED')),
    CONSTRAINT chk_card_type  CHECK (card_type  IN ('CREDIT','DEBIT','PREPAID'))
);
GO

-- Non-clustered indexes (realistic production pattern)
CREATE NONCLUSTERED INDEX ix_card_txn_pan          ON dbo.card_transaction (pan);
CREATE NONCLUSTERED INDEX ix_card_txn_pan_token     ON dbo.card_transaction (pan_token);
CREATE NONCLUSTERED INDEX ix_card_txn_merchant      ON dbo.card_transaction (merchant_id, txn_timestamp DESC);
CREATE NONCLUSTERED INDEX ix_card_txn_status        ON dbo.card_transaction (txn_status, txn_timestamp DESC);
CREATE NONCLUSTERED INDEX ix_card_txn_timestamp     ON dbo.card_transaction (txn_timestamp DESC);
CREATE NONCLUSTERED INDEX ix_card_txn_rrn           ON dbo.card_transaction (retrieval_ref_num);
GO

-- ---------------------------------------------------------------------------
-- Enable CDC on the database and table
-- (Requires SQL Server Agent running and sysadmin / db_owner)
-- ---------------------------------------------------------------------------
-- EXEC sys.sp_cdc_enable_db;
-- GO
-- EXEC sys.sp_cdc_enable_table
--     @source_schema   = N'dbo',
--     @source_name     = N'card_transaction',
--     @role_name       = NULL,
--     @supports_net_changes = 1;
-- GO
-- ---------------------------------------------------------------------------

-- Verify
SELECT
    t.name                          AS table_name,
    c.name                          AS column_name,
    tp.name                         AS data_type,
    c.max_length,
    c.is_nullable
FROM sys.tables t
JOIN sys.columns c  ON c.object_id = t.object_id
JOIN sys.types  tp  ON tp.user_type_id = c.user_type_id
WHERE t.name = 'card_transaction'
ORDER BY c.column_id;
GO
