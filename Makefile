PYTHON = python

src/jntajis/_jntajis.h: src/jntajis/gen.py jissyukutaimap1_0_0.xlsx mji.00601.xlsx MJShrinkMap.1.2.0.json
	$(PYTHON) -m jntajis.gen -- src/jntajis/_jntajis.h jissyukutaimap1_0_0.xlsx mji.00601.xlsx MJShrinkMap.1.2.0.json

mji.00601.xlsx: mji.00601-xlsx.zip
	unzip -o $< $@
	touch $@

mji.00601-xlsx.zip:
	curl -L -o $@ https://moji.or.jp/wp-content/mojikiban/oscdl/mji.00601-xlsx.zip

MJShrinkMap.1.2.0.json: MJShrinkMapVer.1.2.0.zip
	unzip -o $< $@
	touch $@

MJShrinkMapVer.1.2.0.zip:
	curl -L -o $@ https://moji.or.jp/wp-content/mojikiban/oscdl/MJShrinkMapVer.1.2.0.zip

jissyukutaimap1_0_0.xlsx: syukutaimap1_0_0.zip
	unzip -o $< $@
	touch $@

syukutaimap1_0_0.zip:
	curl -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.101 Safari/537.36." -L -o $@ https://www.houjin-bangou.nta.go.jp/download/images/syukutaimap1_0_0.zip
