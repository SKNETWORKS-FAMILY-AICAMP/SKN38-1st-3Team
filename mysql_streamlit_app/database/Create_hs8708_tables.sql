-- 기존 Table 삭제

DROP TABLE IF EXISTS trades;
DROP TABLE IF EXISTS parts;
DROP TABLE IF EXISTS stats;


-- -------------------------------------------------------------------------------------------------------
-- Table 생성

CREATE TABLE parts (
	hsCd	varchar(15)	NOT NULL,
	hsKor	varchar(100)	NULL,
	hsExp	varchar(150)	NULL
);

CREATE TABLE trades (
	year	varchar(10)	NULL,
	hsCd varchar(15)	NOT NULL,
	statCd	varchar(5)	NOT NULL,
	expDlr	double	NULL,
	expwgt	double	NULL,
	impDlr	double	NULL,
	impwgt	double	NULL,
	balPayments	double	NULL
);

CREATE TABLE stats (
	statCd	varchar(5)	NOT NULL,
	statKor	varchar(100)	NULL,
	statEng	varchar(100)	NULL
);

ALTER TABLE parts ADD CONSTRAINT `PK_PARTS` PRIMARY KEY (
	hsCd
);

ALTER TABLE trades ADD CONSTRAINT `PK_TRADES` PRIMARY KEY (
	year,
	hsCd,
	statCd
);

ALTER TABLE stats ADD CONSTRAINT `PK_STATS` PRIMARY KEY (
	statCd
);

ALTER TABLE trades ADD CONSTRAINT `FK_parts_TO_trades_1` FOREIGN KEY (
	hsCd
)
REFERENCES parts (
	hsCd
);

ALTER TABLE trades ADD CONSTRAINT `FK_stats_TO_trades_1` FOREIGN KEY (
	statCd
)
REFERENCES stats (
	statCd
);

