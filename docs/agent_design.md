# Agent design

The agent runs in Copilot Studio with standard orchestration (topics with fixed questions, no generative orchestration). It speaks German, because the people using it would be workers on a German shop floor. The full topic is in `copilot-studio/topics/FehlerMelden.mcs.yml`.

## Topic "Fehler melden"

Trigger phrases are things like "Ich möchte einen Fehler melden", "Die Teile sind undicht" or "Kratzer an Station 32 auf Linie 3, 5 Teile".

### Reading the first message

Before any question, the topic looks at the first message with three patterns (Power Fx `Match`, case insensitive).

| Value | Pattern |
|---|---|
| Line | `(linie\|line)\s*l?\s*(?<nr>[0-3])\b` |
| Station | `station\s*s?\s*(?<nr>\d+)` |
| Number of parts | `(?<nr>\d+)\s*(teile\|teil\|stück\|stk)` |

A value found this way is checked with the same rules as an answer to a question. A station that does not exist on the line is dropped with a short hint, and the agent asks for it.

### Questions

Each question is only asked if the value is still empty.

| Variable | Question | Type | Check |
|---|---|---|---|
| `LinieNr` | Auf welcher Linie ist das passiert? | Number | 0, 1, 2 or 3 |
| `StationNr` | Und an welcher Station auf Linie {Linie}? | Number | must exist on that line |
| `Fehlerart` | Was für ein Fehler ist es? | closed list | Kratzer, Maßabweichung, Undichtigkeit, Sonstiges |
| `Anzahl` | Wie viele Teile sind betroffen? | Number | whole number from 1 to 1000 |
| `Beschreibung` | Beschreib kurz, was du gesehen hast. | text | |

Synonyms for the defect list: Kratzer (verkratzt, Riefe, Kratzspuren), Maßabweichung (Maß, zu groß, zu klein, Toleranz), Undichtigkeit (undicht, leckt, Leck, Leckage), Sonstiges (anderes).

The line was a closed list L0 to L3 at first. Copilot Studio also accepts the position in a list, so "3" was read as the third entry (L2). That is why the line is a number question now.

### Station check

| Line | Stations |
|---|---|
| L0 | S0 to S23 |
| L1 | S24, S25 |
| L2 | S26 to S28 |
| L3 | S29 to S51 (no S42, no S46) |

Validation of the station question:

```
Mod(Topic.StationNr, 1) = 0 && Switch(Topic.Linie,
    "L0", Topic.StationNr >= 0 && Topic.StationNr <= 23,
    "L1", Topic.StationNr >= 24 && Topic.StationNr <= 25,
    "L2", Topic.StationNr >= 26 && Topic.StationNr <= 28,
    "L3", Topic.StationNr >= 29 && Topic.StationNr <= 51 && Topic.StationNr <> 42 && Topic.StationNr <> 46,
    false)
```

`StationID` is `Topic.Linie & "_S" & Text(Topic.StationNr)`, which matches `station_id` in Power BI.

### Confirmation

The agent shows a summary and asks "Passt das so?". On yes it calls the flow and answers with the first eight characters of the report ID. On no it clears line, station and number of parts and starts again.

## Flow "QM Meldung speichern"

Trigger "When an agent calls the flow" with six text inputs (Line, Station, StationID, DefectType, Quantity, Description).

1. Compose `ReportID` with `guid()`
2. Excel Online (Business), "Add a row into a table", file `QM-Fehlermeldeassistent/qm_reports.xlsx` on OneDrive, table `Reports`, Timestamp `utcNow()`
3. Respond to the agent with `ReportID`

The definition is in `copilot-studio/flow/qm_meldung_speichern.json`.

## Topic "Fehlercode erklären"

The second topic answers questions about defect codes from the example catalogue in knowledge/Fehlerkatalog.pdf.

1. The code is read from the question with the pattern `\b(?<b>[kmus])\s*-?\s*(?<n>\d{3})\b` and written as letter, hyphen, number (k102 becomes K-102). If there is no code, the agent asks for it.
2. A station in the question is read with the same pattern as in the report topic. A station that does not exist (above 51, or 42 or 46) gets a short hint.
3. A code that is not among the 11 catalogue codes is rejected with a fixed message. No search and no model call happen in this case.
4. For a known code the topic calls generative answers (SearchAndSummarizeContent) on the knowledge source. The search text contains the code, the station if there is one, and the original question. Additional instructions tell the model to answer only from the catalogue, to name stations, causes, first measure and escalation, to point out a station that is not listed for the code and to say when the catalogue has no answer.

The system topic "Mehrere passende Themen" has one extra rule. If a message contains a code and "Fehlercode erklären" is one of the matching topics, that topic is chosen without asking the worker. Without this rule, short questions like "Was bedeutet Fehlercode U-303?" matched both topics.

The agent instructions repeat the rules for catalogue answers, and the fallback topic (Konversationsboosting) uses the same additional instructions for general questions.
