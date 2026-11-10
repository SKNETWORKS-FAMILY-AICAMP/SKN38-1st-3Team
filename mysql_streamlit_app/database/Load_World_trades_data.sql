DELETE FROM trades
WHERE statCd = "-" OR hsCd = 8708000000;

INSERT INTO trades (YEAR, hsCd, statCd, expDlr, expwgt, impDlr, impwgt, balPayments)
(
	SELECT t.YEAR, "8708000000", t.statCd, sum(t.expDlr), sum(t.expwgt), sum(t.impDlr), sum(t.impwgt), sum(t.balPayments)
	FROM trades t
	GROUP BY t.YEAR, t.statCd
);

INSERT INTO trades (YEAR, hsCd, statCd, expDlr, expwgt, impDlr, impwgt, balPayments)
(
	SELECT t.YEAR, t.hsCd, "-", sum(t.expDlr), sum(t.expwgt), sum(t.impDlr), sum(t.impwgt), sum(t.balPayments)
	FROM trades t
	GROUP BY t.YEAR, t.hsCd
);