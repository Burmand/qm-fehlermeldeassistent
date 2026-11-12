# Test protocol: knowledge source

Date 12.11.2026, Copilot Studio test chat, knowledge source Fehlerkatalog.pdf (status Ready), web search off, general knowledge off.

| # | Input | Expected | Result | Status |
|---|---|---|---|---|
| 1 | Was bedeutet Fehlercode M-204? | Entry from the catalogue with source | Name, stations L3 S32 and S33, causes, first measure and escalation exactly as in the catalogue, source Fehlerkatalog.pdf | passed |
| 2 | Was muss ich bei k102 tun? | Code recognised in other spelling | Answered as K-102 with all fields and source | passed |
| 3a | Was bedeutet Fehlercode U-303 und was ist zu tun? (first version, U-303 still on the list of known codes) | No invented answer | Generative answer said U-303 is not in the catalogue and gave no causes or measures | passed |
| 3b | Was bedeutet Fehlercode U-303? (final version) | Rejected before any search | "Den Code U-303 gibt es im Fehlerkatalog nicht..." from the code check | passed |
| 4 | Was bedeutet Fehlercode M-204 an Station 42 und was ist zu tun? | Hint about the station, then the code | Hint that station 42 does not exist, then the M-204 entry with the remark that the code is listed for S32 and S33 only | passed |
| 5 | Was muss ich bei K-101 an Station 30 tun? | Point out that the code does not belong to S30 | Said K-101 is listed for L0 S0 and S1, not S30, and asked to check the code. No measures invented for S30 | passed |
| 6 | Kratzer an Station 0 auf Linie 0, 2 Teile, then a description and "ja" | Report saved as before | Asked only for the description, showed the summary, saved with reference number 5be19116 | passed |
| 7 | auf Linie 3 an Station 42 sind 2 Teile undicht | Station check in reports still works | Station 42 rejected with the list of valid L3 stations, then asked for the station | passed |

## Problems found during testing

- In the first run, "Was bedeutet Fehlercode U-303?" matched both topics, so the agent asked "Meinten Sie" with both options. After choosing one, the topic only saw the button text and had to ask for the code again. More trigger phrases did not help. The fix is a rule in the system topic for multiple matches. If the message contains a code like U-303, the topic "Fehlercode erklären" is chosen without asking.
- Test 3a ran against an older list of known codes, so the question reached the generative answer instead of the code check. The model still refused to invent an answer, which is a useful result on its own.
- In test 5 the answer added the general rule from the catalogue (report faults that are not listed directly to quality assurance). This is correct for the catalogue but goes a little beyond the question.
