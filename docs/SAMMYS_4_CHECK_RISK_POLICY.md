# SAMMY'S 4-CHECK RISK POLICY & OPERATIONAL MANUAL
**Position:** Head of Risk & Beta Program Coordinator  
**Target Account:** Sajim Holdings Live / Prop / Cent Accounts (0.01 Lot)  
**Authority:** Checklist Verification Only (No Unilateral Policy Modification)

---

## 1. THE GOLDEN RULE / SHERIA KUU
> **"Sammy is the Risk Checker, NOT the Risk Maker."**  
> Wewe ni dereva wa breki, sio mjenzi wa injini. Kama taa 4 zote ni GREEN (YES), gari linakwenda (GO). Kama taa moja ikiwa RED (NO), gari linasimama (STOP).  
> Sammy cannot invent new rules, cannot block a valid trade that passes all 4 checks, and cannot authorize a bad trade that fails any check.

---

## 2. THE 4-CHECK GATEKEEPER CARD (KARATASI YA UKAGUZI)

Kabla trade yoyote haijawekwa live au kutumwa kwa WhatsApp broadcast bot ya Tete, Sammy lazima athibitishe vipengele hivi 4 kutoka kwa BEEP Dashboard / API:

| # | Check Item | Parameter / Condition | Result | Maelezo |
|---|:---|:---|:---:|:---|
| **1** | **Mass Momentum $M(t)$** | Is $M(t) > 40$? | [ ] YES &nbsp; [ ] NO | Kama $M(t) \le 40$, hakuna nguvu ya kutosha sokoni. Subiri. |
| **2** | **Baseline Floor $B(t)$** | For BUY: Is $SL < B(t)$?<br>For SELL: Is $SL > B(t)$? | [ ] YES &nbsp; [ ] NO | Stop Loss lazima ilindwe na baseline ya BEEP ili kuepuka spikes za uongo. |
| **3** | **Position Sizing** | Is Lot Size strictly **0.01**? | [ ] YES &nbsp; [ ] NO | Hakuna tamaa. Account ya kuanzia (cent/prop) lazima itumie 0.01 lot pekee. |
| **4** | **Energy Factor $\Lambda(t)$** | Is $\Lambda > 10\%$? | [ ] YES &nbsp; [ ] NO | Volatility lazima iwe hai. Kama soko limelala, hatuingii. |

### The Execution Decision:
* **Zote 4 zikiwa YES:** Sammy anasema $\rightarrow$ **"GO"** (Trade inaruhusiwa).
* **Moja tu ikiwa NO:** Sammy anasema $\rightarrow$ **"STOP"** (Hakuna trade).

### Founder Override (Mamlaka ya Mwanzilishi):
Kama trade imefaulu vigezo vyote 4 lakini Sammy anaiwekea mashaka binafsi (hisia, hofu, au maoni ya nje), **Jimmy (Founder) ana mamlaka kamili ya ku-override na kuamuru trade iendelee.**

---

## 3. BETA PROGRAM SALES PROTOCOL (100 KES LAB FEE)

### Objective:
Kuleta wanafunzi 50–100 kila wiki kulipia **KES 100** ili kufadhili gharama za VPS Server na Data bila kuchukua mikopo ya benki au m-pesa.

### Rules of Engagement:
1. **Never call it "Investment" or "Forex Account Management":**
   - Haturuhusiwi kusema "tupe 100 tukutengenezee faida" (hiyo ni kosa la kisheria).
   - Tunauza mafunzo na uthibitisho wa teknolojia: **"BEEP Student Beta — 100 KES Lab Fee"**.
2. **What Students Receive:**
   - Jaribio la BEEP kwenye **Demo Account yao binafsi** (0.01 lot).
   - Masaa 24 ya kupokea alerts kutoka WhatsApp bot.
   - 100% ya faida ya demo inabaki kwao; Sajim haichukui chochote.
3. **Sammy's Commission:**
   - Sammy anapata **20% ya ada zote za wanafunzi** (mfano: wanafunzi 50 = KES 5,000; Sammy anapata KES 1,000 cash).

---

## 4. SIGNATURE & COMMITMENT

Nathibitisha kuwa nimesoma na kuelewa majukumu yangu kama Mkuu wa Risk. Nitaendesha ukaguzi kwa kufuata vigezo hivi 4 bila kuweka hisia wala kubadilisha sera.

**Sammy (Head of Risk):** _____________________________ **Date:** ______________  
**Jimmy Mathu (CEO / Founder):** _______________________ **Date:** ______________
