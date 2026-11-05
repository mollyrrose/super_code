# Stíluselemzés: Seal Josephson (Fodor-Josephson Szilárd)

Könyv: *Szakmai intuíció a vezetői döntéshozásban — Csípőből Tüzelünk*
Készült: 2026-11-05

## Források és módszer

1. **A szerző saját szövegei**
   - 48 magyar HR Portál-cikk (`content/rebased/_backup/articles.json`, `lang: "hu"`, kb. 690 000 karakter). Ezekből olvastam: Bevezető, I.1 Közgazdaságtan, I.2 Fizika, Ki a Főnök?, a 80%-os cikk, HR KPI 11 (AQ), a 3DS-cikk és a KvantHumanisztika-cikkek. A teljes korpuszon gépi számlálás is futott.
   - Angol kéziratok (`content/source/manuscripts/*.txt`): introduction, economics, biology, sociology, psychology, philosophy-1.
   - Figyelem: a `philosophy-1.txt` egyes részein már AI-ízű szavak vannak („delve”, „intricate”, „paramount”), tehát valószínűleg AI-segítséggel készült. Ezért stílusmintának kisebb súllyal vettem figyelembe.
2. **AI-szöveg és a szerző javítása**: 6 pár (`in_I.4` ... `in_I.11`), 431 AI-bekezdés és 601 javított bekezdés. A bekezdéseket szóátfedés alapján párosítottam, és jelölőket számoltam (felkiáltójel, gondolatjel, zárójel, perjel, „nem ... hanem”).
   - A gépi fordítás hibáit (szórend, „professzionális intuíció”, „örömteli kilátás”, „Boldog Elmeállapot”, „Tudatossági Intelligencia”, „Ön”-forma, „GOLD/CORAL/TURQUOISE” angol színnevek) nem tekintettem a szerző stílusának.

Kalibráló számok, 10 000 karakterre vetítve:

| Jelölő | Szerző saját HU cikkei | AI-szöveg | Szerző javítása (visszafordítva) |
|---|---|---|---|
| `!` | 2,3 | 0,06 | 6,7 |
| `?` | 8,5 | 7,8 | 7,9 |
| „nem ... hanem” | 1,7 | 3,0 | 1,9 |
| gondolatjel `–` | 9,5 (` - ` is) | 14,7 | 9,2 |
| perjel (`vállalat/társadalom`) | 8,4 | 0,2 | 27,4 |
| zárójel | 8,0 | 9,2 | 32,3 (a fordítás felfújja) |

A mondathossz mindhárom korpuszban szinte azonos: medián 14 szó, átlag 15–16 szó. A különbség tehát a bekezdések hosszában és a hangvételben van. Átlagos bekezdéshossz: AI 379 karakter, javítás 293 karakter.

---

## A) A szerző saját stílusa

### A1. Hangnem: lelkes, közvetlen, önironikus, magasztos és hétköznapi egyszerre

Lelkesen, jó szándékkal ír, és vállaltan „terjeszt”. Ünnepélyes, néha archaikus szavak (ilyetén, mitöbb, recens, aposztrofálhatjuk) keverednek szleng- és humoros fordulatokkal. Gyakran gúnyolja saját magát.

- „E jószándékú cikkíró előrebocsájtja, hogy nem rendelkezik kvantumfizikusi végzettséggel. Mindemellett, van két jó szeme, lassan, de legalább tud olvasni, omega-3 halolajat és Lugol jód oldatot szed…”
- „Beosztott, vagy menedzsment szinteken általában ezt alkalmazzuk döntéseink helytállóságának megindokolására – nemes hátsó fertályunk levédéseképp -.”
- „(Vezetői statisztikák biztosítására specializálódott IT cégek és szolgáltatók most kapnak a szívükhöz.)”

Nagy, kerek ígéreteket és értékítéleteket is kimond, kertelés nélkül („Az éberség intelligencia fejlesztésével töltött idő minden perce legalább tízszeres előnnyel tér vissza.”). A társadalmi és vallási kérdésekben is éles véleményt mond (sociology, I.8). Ezt a vonását csak akkor szabad átvenni, ha a szerző maga adja az állítást. Claude ne találjon ki ilyet.

### A2. Nézőpont és megszólítás

- **Uralkodó a többes szám első személy („mi”)**: „-unk/-ünk” végződés 38-szor 10 000 karakterenként. „Hogyan válhatunk hát hatékonyabbá ilyetén célunk elérésében?”
- **Magáról harmadik személyben, ironikusan ír** a magyar cikkekben: „e cikkíró”, „e jószándékú író”, „e tiszteletteli író”, „ez írót beleértve”. Angolul: „this author”, „this respective author”.
- **Személyes anekdotánál az angol javításban első személyre vált**: „A Samsungnál töltött időm alatt számos heti jelentést készítettem…”, „Tapasztaltam már az ellenkezőjét is.”
- **„Kedves Olvasó”** ritkán szerepel (0,16 / 10 000 karakter), és csak ünnepélyes pontokon: „Némi patetikus túlzással azt kívánja ezen cikk írója, hogy a Kedves Olvasó értékelje a mai nap legjobb híreként azt, hogy az intuíció létjoga tudományosan bizonyított…” Angolul: „the kind reader”, „Ladies and gentleman”.
- **Felhívásban és gyakorlatban tegez**: „Megtennéd légy kedves azt a szivességet…”, „Tekintsd meg az angol nyelvű videót…”. A javításokban a gyakorlatok felszólító módban, tegezve szólnak: „Csak ülj le öt percre ebéd után…”.

### A3. Mondathossz és ritmus

A mondatok átlagosan közepes hosszúak, de a hosszúság erősen hullámzik. Két-három hosszú, beékelésekkel teli mondatot egy rövid, csattanós mondat zár.

- „Közgazdász nyelven kifejezve, többet fizetünk és kevesebbet kapunk.”
- „A hamburgerben a hús érdekel minket.”
- „Annyit kell csak tennünk, hogy bennemaradunk a tér tapasztalatában, és hagyjuk, hogy az információk felbugyogjanak. Majd egyszerűen ismerjük fel azokat. És, ennyi.”

Beékelésre a ` - ... -` és a `– ... –` szerkezetet használja, gyakran a mondat végén is: „…– mondja Kahneman -.” Felkiáltójellel nyomatékosít, a saját szövegeiben mértékkel.

### A4. Kedvelt szerkezetek

- **Kérdés, aztán azonnal felkiáltó válasz**: „Hogyan válhatunk hát hatékonyabbá…? Hatékonyabb, gyorsabb döntésekkel!” A javításban: „Hogyan szokhatunk hozzá? Gyakorlással!”
- **Perjeles alternatívák és halmozott szinonimák**: „felhalmozás/az örömteli látásmód útja”, „tudatunk/ tudatosságunk/ éberségünk (bárhogy is nevezzük)”, „belső hang, megérzés, ráérzés, jövőbe látás, hatodik érzék, szívünkre hallgatás”.
- **Zárójeles angol glossza a szakszó után**: „éberség-intelligenciának (ang. awareness intelligence, AQ)”, „rendszergondolkodás (ang., systems thinking)”.
- **`(!)` nyomatékjel számadat után**: „46% (!) nagyon gyakran”, „902 fő (!) válaszadóval”.
- **Kötőszavak és fordulatok**: „Mindemellett”, „Ezzel szemben”, „Tehát”, „Egyszerűen”, „mondhatjuk”, „érdemes”, „Nézzük, …”.
- **Ismétlő, mantraszerű tanítómondat**: „Minden a térben jelenik meg, abban játszik, majd a térbe tér vissza.” Ez szinte változatlanul tér vissza több cikkben.

### A5. Kérdések

Sok kérdést használ (8,5 / 10 000 karakter). Kérdéssel nyitja a cikket, kérdés a köztes cím is, és sorozatkérdéssel gondolkodtat.

- Nyitás: „Hogy működik az intuíció fizikai szinten? Megfigyelhető-e összekapcsolódás az intuíció és természettudományunk éke a fizika között?”
- Köztes cím: „Az intuíció női tudomány?”, „Biztos, hogy nem csak ugrattok?”, „Mitől több az AQ mint az IQ?”
- Gondolkodtató sor: „Ő lát minket és mi nem látjuk? Mi létezünk számára, számunkra viszont ő nem létezik?”

### A6. Metaforák és hasonlatok

Hétköznapi, kézzelfogható, gyakran testi vagy konyhai képeket használ, emellett közgazdasági és filmes utalásokat. Néhány kép újra és újra visszatér:

- **Nap és felhők** (a tudat napja, a gondolatok felhői): „intuíciónk átvághatja gondolataink és érzéseink felhőit, mint mikor a napsugarak átragyognak az ég felhőin.”
- **Óceán és hullámok, mozivászon és film, tükör.**
- **Ház** (értékrend = alap, örömteliség = tető), **jéghegy** (AQ-szintek), **vödör két kézben** (AQ és HM egyensúlya).
- **Edzés**: „Ha már amúgy is csinálunk mondjuk fekvőtámaszt, akkor miért ne látogatnánk meg egy edzőteremet?”; „Az agyunk egy izom”.
- **Közgazdasági nyelv az élet dolgaira** (EN): „investing in bodily health seems like a profitable business; still, it is an unavoidable bear market from the long-term perspective.”
- **Testrész-humor**: „Kezdjük azzal ami orrunk előtt- és ami homloklebenyünk mögött van.”; „a 'két szép szemünk'”.
- **Popkultúra**: Star Wars („Yoda Mester, Luke Skywaker (Légjáró Lukács)”), X-Men, Mátrix, Star Trek-szerű „doktori szint” kép.

### A7. A példák forrásai

1. **Saját vezetői pálya**: Canon, Samsung (a konyhai cappuccino-jelenet: „Why are we killing each other here?”), NBCUniversal, a Happiness Consulting és a Happiness Guardian Holding alapítása.
2. **Saját felmérés**: 902 válaszadó, 83%, 37% / 46%, nemek és országok szerinti bontás. Visszatérő horgony.
3. **Nevesített kutatók és tudósok**: Kahneman, Gigerenzer, Einstein, Böhm, Schrödinger, Neumann, Wigner, Faggin, Jung, Graves (Spiral Dynamics), HeartMath Institute, Gallup, Forbes.
4. **Tanítók és hagyomány**: Michael Fuchs („the founder of awareness intelligence concept, whom this author considers to be his mentor”), Mahámudrá, Tilopa és Naropa, a Karmapák (csak Thaye Dorje vonala), a dharmakája / szamboghakája / nirmánakája.
5. **Hétköznapi vagy anekdotikus eset**: a repülős feleség megérzése, az édesanya, aki 300 km-ről megérzi a gyerekét, a telefon, amire épp akkor gondolunk, amikor hívnak.

A forrást római vagy kis római számos lábjegyzettel jelöli (`(i)`, `(ii)`), és a cikk végén „Háttéranyagok” cím alatt listázza.

### A8. Szakkifejezések és következetes terminológia

A kanonikus alakok a `content/glossary.json` szerint:

| HU (kanonikus) | EN | Megjegyzés |
|---|---|---|
| szakmai intuíció | professional intuition | A régi cikkekben „professzionális / szakértői intuíció” is előfordul. Új szövegben: **szakmai intuíció**. |
| éberségintelligencia (AQ) | Awareness Intelligence (AQ) | A régi cikkekben külön írva („éberség intelligencia”). Új szövegben egybe, mindig (AQ)-val. |
| Örömteli látásmód (HM) | Happy Mindset (HM) | Soha nem „örömteli kilátás”. |
| felelősségteljes örömteliség (RH) | Responsible Happiness (RH) | Soha nem „felelős boldogság”. A „felelősségteljes”-t így magyarázza: „nem csak vigyorgunk szakadatlanul”. |
| a felhalmozás útja / az éberség útja | path of accumulation / path of awareness | Az intuíció fejlesztésének két útja (HM, illetve AQ). |
| 3DS / 3DO / 4DS / 4DO gyakorlat | 3DS / 3DO / 4DS / 4DO practice | A kódokat nem fordítjuk. |
| 4D téridő, a tudat 4D téridő-szerű természete | 4D SpaceTime | Visszatérő zárómondat: „A szakmai intuíció gyakorlati fejlesztése a tudatosság 3D-s természetén túlnyúló 4D-természetű tudatunk természetéhez való hozzászokással történik.” |
| tér-természet, térszerű, teresség | space-nature, space-like | |
| tudat / tudatosság / éberség / figyelem | mind / consciousness / awareness / focused attention | Négy külön fogalom, nem cserélhetők fel. |
| KvantHumanisztika, KvantHumanizmus | QuantHumanistics, QuantHumanism | CamelCase. |
| jól-lét (fizikai, interperszonális, mentális) | well-being | Kötőjellel. |
| SDx (Spiral Dynamics Extended), értékrend, memetika | value system, memetics | |

**SDx színek**: nagybetűvel, magyarul írja: BÉZS, LILA, PIROS, KÉK, NARANCS, ZÖLD, SÁRGA, TÜRKÍZ. Vegyes szintnél kötőjellel, a hangsúlyos szín nagybetűs: „KÉK-Piros”, „ZÖLD-Sárgák”. Az angol kéziratban a felső szintek: CORAL, TEAL, GOLD, LIME. A magyar megfelelőkre az AI a KORALL, KÉKESZÖLD, ARANY, LIME alakot használta, de ezek a glosszáriumban nincsenek benne. **Ezt a tulajdonossal jóvá kell hagyatni.** A javított I.6-ban a TEAL helyén „TURQUOISE” áll: ez fordítási hiba, nem a szerző döntése.

### A9. Bekezdés- és fejezetszerkezet

- **Nyitás**: mottó vagy idézet (Einstein), egy rövid jelenet, vagy 2–3 kérdés, majd azonnal a tartalom. A HR Portál-cikkeknél a lead maga a kérdéssor.
- **Köztes címek**: rövidek, sokszor kérdések vagy kiemelt idézetek (pull-quote: „"az intuíció nem női kiváltság; férfiak és a nők is egyaránt élnek vele"”).
- **Bekezdés**: 1–6 mondat. Az egymondatos bekezdés gyakori, főleg csattanónál.
- **Listák**: számozott jellemzők (I., II., III.), lépések (Gigerenzer négy lépése), SDx-példák. A listát nem kerüli, ha tényleg lépésekről van szó.
- **Zárás**: „vége” jelzés, sorozatnavigáció, a 3D/4D gyakorlatra mutató standard bekezdés és egy felhívás („Kövesd a cikksorozatot!”). A könyvfejezet-javításokban a zárás egy elvégezhető gyakorlat vagy egy kérdés („Kezdjük el a gyakorlást?”).

---

## B) Mit változtatott a szerző az AI-szövegen

A gyakoriságok a 6 pár gépi párosításán alapulnak, ezért becslések. A szöveg hossza +8%-kal nőtt (163 000 karakterről 176 000-re), a bekezdések száma +39%-kal (431-ről 601-re).

| # | Változás típusa | Gyakoriság (becslés) | Előtte (AI) | Utána (szerző) |
|---|---|---|---|---|
| B1 | **Kihúzta a fejezettérképet és a meta-kommentárt** („Ebben a fejezetben végigjárjuk…”, „A fejezet három részből áll”, „Az I. modul eddigi fejezeteiben…”). | Minden fejezetben, ahol volt (6/6). Ez a 144 párosítatlan AI-bekezdés jelentős része. | I.10: „Ebben a fejezetben végigmegyünk a traumaoldás létráján, megnézzük, hogyan dolgoztak a pszichológia nagyjai…” | Csak a kérdés marad: „Miért traumafeldolgozás, ha intuíciót keresünk?” |
| B2 | **Szétvágta a hosszú bekezdést**: rövidebb bekezdések, sok új rövid köztes cím. | Az AI-bekezdések kb. 22%-a (93 db) két vagy több részre esett. A rövid sorok (cím, töredék) száma 81-ről 165-re duplázódott. | I.11: egy 6 forrást felsoroló bekezdés. | 6 külön sor, mindegyik végén zárójeles forrással: „…18–43%-kal alacsonyabb a fluktuációjuk (Gallup Q12 metaanalízis…, 2020)”. Új címek: „Két dolog”, „Jelenlét”, „Nyitott tudatosság”. |
| B3 | **Csattanós, rövid nyitást írt** az AI magyarázó nyitása helyett. | 4/6 fejezetnyitás. | I.4: „Csakhogy az idő nem egy mindenütt egyformán ketyegő világóra. Minden térnek megvan a maga mozgása…” | „Hétfő. De melyik hétfő? Az idő mindenhol máshogy telik.” |
| B4 | **Új hétköznapi analógiát és gondolatkísérletet tett be**, gyakran „képzeld el” formában. | Kb. 61 teljesen új bekezdés (a javított szöveg ~10%-a), ezek nagy része ilyen. | I.4: absztrakt Wheeler–DeWitt-magyarázat. | „Képzeld el, hogy egy domboldalon állsz, és nézed, ahogy a felhők elsuhannak… Ha valahogy el tudnád választani minden egyes felhőt a környezetétől, mi maradna? A válasz: semmi.” Ugyanott: a 2D-lapokon élő lény képe. |
| B5 | **Közvetlenül megszólítja és bevonja az olvasót**: kérdést tesz fel neki, és előre válaszol a reakciójára. | Mind a 6 fejezetben. A te-formájú felszólítások 1-ről 19-re nőttek. | I.10: „Hol vannak az emlékeink? A legtöbben azt mondanánk: az agyunkban. Ez csak részben igaz.” | „Valószínűleg azt válaszoltad: Az agyunkban. És igazad is lenne… de csak félig.” |
| B6 | **Elvégezhető gyakorlatot írt az elmélet mellé**, tegező felszólító módban, lépésekkel. | I.9, I.10, I.11, mindegyikben 2–5 új gyakorlat. | I.9: a fejezet egy előremutató mondattal zár: „A következő, I.10. fejezetben a traumaoldás létráján lépkedünk végig…” | „Készíts egy listát minden olyan traumáról, amire gyerekkorodtól kezdve emlékszel, adj mindegyiknek egy rövid, két szavas (számodra!) címet…” Továbbá: „Elvégezhetsz egy mini családállítást magadnak: ülj kényelmesen és csukd be a szemed.” |
| B7 | **Személyes tapasztalatot első személyben írt**; az AI harmadik személyű, kissé modoros „e tiszteletteli szerző” formáját lecserélte. | Minden személyes részletnél (I.11-ben 4 hely). | „ez a tiszteletteli szerző mindhárom korábbi multinacionális munkakörében – a Canonnál, a Samsungnál és az NBCUniversalnál is – új vezetőt kapott…” | „Tapasztaltam már az ellenkezőjét is. Három korábbi munkahelyemen (Canon, Samsung, NBCUniversal) új menedzsereim/vezetőim voltak…” |
| B8 | **Energikusabb, felkiáltó hangot adott**: kérdés és felkiáltó válasz, felkiáltó csattanó. | `!`: 1-ről 118-ra (10 000 karakterenként 0,06-ról 6,7-re). Ebben a fordítás is túloz, a szerző saját szintje 2,3. | „Ez egyszerre biztosítja az intuíció szabadságát és a háttéradatok biztonságát.” | „Mítosz ledöntve: … a férfiak és a nők egyformán gyakran teszik ezt!” Továbbá: „Hogyan szokhatunk hozzá? Gyakorlással!” |
| B9 | **Kihúzta az aforisztikus, „nem X, hanem Y” típusú zárómondatokat és a dramaturgiai felvezetéseket.** | „nem ... hanem”: 49-ről 33-ra. Gondolatjel: 240-ről 163-ra. | „Nem kívülről tanuljuk meg; belülről ismerünk rá.” – „És itt jön a legszebb rész.” – „Érdemes ezen a ponton megszólaltatnunk valakit, aki nem a misztika, hanem a szilícium felől érkezett…” | Tényt közöl, utána száraz humor: „Tehát Faggin tud egyet-mást a mezőkről. És hiszi, hogy a mezők tudatosak.” |
| B10 | **Átrendezte a sorrendet**, hogy a fogalom előbb kapjon képet, és csak utána jöjjön a bizonyíték. | Minden hosszabb fejezetben vannak visszaugrások (I.8: 64, I.10: 46). I.6-ban a KORALL-blokk a végére került. | I.4: Schrödinger és DeWitt → kockacukor-példa. | Előbb felhők és kockacukor („Mi nagyrészt tér vagyunk.”), azután az egyenlet. |
| B11 | **Megelőzi az olvasó kételyét**, ahelyett hogy fenntartást fűzne az állításhoz. | I.4, I.8. | Az AI fenntartása: „Egy figyelmeztetés előre. Az elmélet nem állítja, hogy a természettudomány bebizonyította volna…” (ezt kihúzta) | „Ez egy merész állítás, és sokan nehezen fogják elfogadni. De mielőtt azonnal elvetné, vegye figyelembe, hogy ez a fizika… alapjaira épül.” |
| B12 | **Perjeles alternatívákkal sűrített** a hosszabb körülírás helyett. | Perjel: 3-ról 485-re (részben fordítási hatás, de a saját cikkeiben is 8,4 / 10 000 karakter). | „A KORALL vállalat vagy társadalom – mondhatjuk úgy is, a globális hatalmú vállalat vagy társadalom –” | „A CORAL vállalat/társadalom, mondhatnánk a globálisan erős vállalat/társadalom” |
| B13 | **A zárás gyakorlati hívás vagy kérdés lett**, nem kerek összefoglaló mondat. | 4/6. | „Tegyük meg együtt az első lépést.” | „Hogyan szokhatunk hozzá? Gyakorlással! … Kezdjük el a gyakorlást?” |

Amit **nem** változtatott: a nevesített forrásokat, számokat és évszámokat megtartotta, csak zárójelbe tette őket. A felsorolásokat (Gigerenzer négy lépése, SDx-példák, a ház-modell) is megtartotta. A mondathossz medián szinten nem változott (14 szó).

---

## C) Az AI-szöveg jellegzetes hibái, amelyeket a szerző kerül vagy javít

1. **Fejezettérkép és útjelző mondat**: „Ebben a fejezetben végigjárjuk…”, „Ez a fejezet egy csokorba köti mindezt…”, „A következő fejezetben…”, „Az előző fejezetben láttuk, hogy…”. A szerző kihúzza, vagy egy kérdésre rövidíti („Emlékezzünk…? Nos, itt vagyunk!”).
2. **Kerek, mindent összefoglaló bekezdés**: „Foglaljuk össze, hol tartunk…”, „A nyereség tehát valóban mellékhatás”. A szerző sem kerüli teljesen az összefoglalást („Összefoglalva!”), de rögtön gyakorlatra vagy kérdésre fordítja.
3. **Aforizma-zárás és bináris ellentét**: „Nem miszticizmus, hanem…”, „Nem kívülről tanuljuk meg; belülről ismerünk rá.”, „Nem három különálló emelet ez, hanem egyetlen folyamat.” Az AI ezt majdnem kétszer olyan sűrűn használja (3,0 / 10 000 karakter), mint a szerző (1,7).
4. **Dramaturgiai felvezetés**: „Van azonban egy még beszédesebb képlet.”, „És itt jön a legszebb rész.”, „Innen azonban engedtessék meg egy lépés tovább.”, „Egy fontos megjegyzés ide kívánkozik.”
5. **Túl sima, egyenletes, hosszú bekezdés** sok gondolatjeles beékeléssel (14,7 / 10 000 karakter). A szerző tördel, és rövid bekezdést ír.
6. **Steril, személytelen hang**: hiányzik a humor, az önirónia, a felkiáltás és a „te”. A szerző személyes és játékos.
7. **A szerző modorának utánzása túlzással**: az AI a „jó szándékú író”, „tiszteletteli szerző” formát egymás után többször is beteszi, kötelező díszként. A szerzőnél ez ritka, és mindig van mögötte poén.
8. **Óvatoskodó meta-fenntartás**: „tapasztalati rangsor, nem kutatási eredmény”, „Egy figyelmeztetés előre.” A szerző inkább megnevezi a forrást, vagy előre felel az olvasó kételyére. Ha egy forrás valóban gyenge, a forrásmegjelölés maradjon pontos. Ezt a projekt szabályai is előírják, csak ne prédikációként legyen megírva.
9. **Elmélet gyakorlat nélkül**: az AI leírja a módszert, de nem adja az olvasó kezébe. A szerző lépésről lépésre végigvezeti.
10. **Választékos, de lapos szóhasználat** („végigjárjuk”, „kézzelfoghatóvá válik”, „egy csokorba köti”, „mélyebb rétege”), és a „hiszen” túlhasználata (az AI-ban 12, a javításban 1).
11. **Angolos szerkezet**: „X az, ami…”, „Ez azt jelenti, hogy…” láncok, birtokos halmozás. (A szerző saját szövegeiben is van angolos szórend; ez nem a szerző javításainak fő iránya.)

---

## D) Írási szabálylista új fejezethez (HU és EN)

**Csináld**

1. **Kérdéssel nyiss** (2–3 rövid kérdés vagy egy jelenet), és a második bekezdésben már tartalom legyen. Példa: „Hétfő. De melyik hétfő?”
2. **„Mi”-formában írj** a törzsszövegben. A gyakorlatokat **tegező felszólító módban** írd („Ülj le öt percre…”), angolul „you”-val. Saját élményt első személyben írj („A Samsungnál…”). Az ironikus harmadik személyt („e jószándékú író”) legfeljebb egyszer használd fejezetenként, és csak ha poén van mögötte.
3. **Minden elvont állítás előtt vagy után legyen egy hétköznapi kép**: felhő és nap, óceán és hullám, mozivászon, ház, jéghegy, vödör, edzőterem, kockacukor, papírlap. Előbb a kép, utána a bizonyíték.
4. **Kérdezz, és válaszolj röviden, felkiáltással**: „Hogyan…? Gyakorlással!” Felkiáltójelből fejezetenként kb. 2–4 kell 10 000 karakterre, ne több.
5. **Tördelj**: 1–5 mondatos bekezdés, gyakori rövid köztes cím (kérdés vagy kiemelt mondat). A hosszú, sokforrású bekezdést bontsd soronként egy állításra, a forrás zárójelben álljon a sor végén.
6. **Nevesítsd a forrást**: kutató, intézmény, év, mintanagyság (Kahneman, Gigerenzer, Gallup 2020, saját felmérés: n=902, 37% / 46%). A számadatnál a `(!)` jelet legfeljebb egyszer használd fejezetenként.
7. **Válts regisztert, de tudatosan**: egy-egy választékos szó („ilyetén”, „recens”) és egy-egy játékos fordulat („nemes hátsó fertályunk”, „csíphető nyakon”) jöhet. Az önirónia is belefér.
8. **Rögzített terminológia**: szakmai intuíció; éberségintelligencia (AQ); Örömteli látásmód (HM); felelősségteljes örömteliség (RH); 3DS/3DO/4DS/4DO; 4D téridő; tér-természet; tudat / tudatosság / éberség / figyelem külön fogalomként; SDx-színek NAGYBETŰVEL (KÉK-Piros). Angolul: professional intuition, Awareness Intelligence (AQ), Happy Mindset (HM), Responsible Happiness (RH), 4D SpaceTime, value system. Első előforduláskor magyarul tegyél mellé angol glosszát: „(ang. awareness intelligence, AQ)”.
9. **Adj elvégezhető gyakorlatot** a fejezet végén vagy egy szakasz végén, számozott lépésekkel és időtartammal („napi 15 perc, 8 hét”, „5–10 perc”).
10. **A zárás legyen gyakorlati**: mutass a 3D-ről 4D-re vezető gyakorlatra, vagy tegyél fel egy kérdést az olvasónak („Kezdjük el a gyakorlást?”). Angolul ugyanígy.
11. **Perjelet csak rokon fogalmak egymás mellé állítására használj** („vállalat/társadalom”, „tudatunk/tudatosságunk”). Mondatonként legfeljebb egyet.

**Kerüld**

12. **Fejezettérkép és útjelző mondat**: „Ebben a fejezetben…”, „A fejezet három részből áll”, „Mint az előző fejezetben láttuk…”. Előre- és visszautalás csak egy rövid kérdésben lehet („Emlékszel a 95/5%-ra?”).
13. **„Nem X, hanem Y” aforizma** bekezdés végén, és dramaturgiai felvezetés („És itt jön a legszebb rész.”, „Van azonban egy még beszédesebb…”). Mondd ki egyenesen az Y-t.
14. **Kerek, mindent ismétlő összefoglaló bekezdés.** Ha kell összefoglalás, egy mondat legyen, utána jöjjön a gyakorlat.
15. **Meta-fenntartás prédikációként** („Egy figyelmeztetés előre…”). Ha egy állítás vitatott, írd le, ki vitatja, egy fél mondatban, vagy felelj előre az olvasó kételyére („Merész állítás. De…”).
16. **Gépi fordítás nyomai** magyar szövegben: „professzionális intuíció”, „örömteli kilátás”, „felelős boldogság”, „Tudatossági Intelligencia”, „Boldog Elmeállapot”, „Ön”-forma, angol színnevek (GOLD, CORAL). Angol szövegben kerüld az AI-szavakat: delve, intricate, paramount, tapestry, realm.
17. **Hosszú, egyenletes bekezdés sok gondolatjellel.** Gondolatjelből legfeljebb kb. 1 jusson 1000 karakterre.
18. **Kitalált anekdota, szám vagy idézet a szerző nevében.** Csak a forrásokban szereplő életrajzi elemet használd (Canon, Samsung, NBCUniversal, Happiness Consulting, Michael Fuchs, a 902 fős felmérés). Éles vallási vagy politikai ítéletet ne írj magadtól.

**Angol nyelvre külön**

- A szerző angolja közvetlen és kicsit „hunglish”: „still,” gyakori kötőszó, ` - ... -` beékelés, „the kind reader”, „this author”. Új angol szöveg legyen helyes amerikai angol (program, behavior), de a hang maradjon ugyanez: kérdésnyitás, képek, rövid felkiáltó válaszok, gyakorlat a végén. Mintamondatok: „The last shirt has no pockets.”, „this author does not sell any life insurance here.”

---

## Nyitott kérdés a tulajdonosnak

Az SDx felső szintjeinek (CORAL, TEAL, GOLD, LIME) magyar neve nincs a `content/glossary.json`-ban. Az AI a KORALL, KÉKESZÖLD, ARANY, LIME alakot használta. Ezt egy új fejezet előtt jóvá kell hagyni.

Megoldva 2026-11-05: a `content/glossary.json` spiral_levels 9-12 tartalmazza: KORALL (CORAL), KÉKESZÖLD (TEAL), ARANY (GOLD), LIME (LIME).
