# jntajis-python

## What's this

![](https://www.houjin-bangou.nta.go.jp/download/images/moji-code.jpg)

```python
import jntajis

print(jntajis.jnta_shrink_translit("麴町"))  # outputs "麹町"
print(jntajis.mj_shrink_candidates("髙島屋"))  # outputs ["高島屋", "髙島屋"]
```

## License

The source code except `src/jntajis/_jntajis.h` is published under the BSD 3-clause license.

`src/jntajis/_jntajis.h` contains the data from the following entities:

* JIS shrink conversion map (国税庁: JIS縮退マップ)

  Publisher: National Tax Agency

  Author: unknown

  Source: https://www.houjin-bangou.nta.go.jp/download/

  License: public domain? (needs to be clarified.)

* MJ character table (文字情報技術促進協議会: MJ文字一覧表)

  Publisher: Character Information Technology Promotion Council (CITPC)

  Author: Information-technology Promotion Agency (IPA)

  Source: https://moji.or.jp/mojikiban/mjlist/

  License: CC BY-SA 2.1 JP

* MJ shrink conversion map (文字情報技術促進協議会: MJ縮退マップ)

  Publisher: Character Information Technology Promotion Council (CITPC)

  Author: Information-technology Promotion Agency (IPA)

  Source: https://moji.or.jp/mojikiban/map/ 

  License: CC BY-SA 2.1 JP
