PYTHON = python

src/jntajis/_jntajis.h: jissyukutaimap1_0_0.xlsx src/jntajis/gen.py
	$(PYTHON) -m jntajis.gen -- jissyukutaimap1_0_0.xlsx src/jntajis/_jntajis.h

jissyukutaimap1_0_0.xlsx: syukutaimap1_0_0.zip
	unzip -o $<

syukutaimap1_0_0.zip:
	curl -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.101 Safari/537.36." -L -o $@ https://www.houjin-bangou.nta.go.jp/download/images/syukutaimap1_0_0.zip
