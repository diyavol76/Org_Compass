---
id: satinalma-talep-akisi
type: workflow-extraction
title: "Satın alma talebi onay ve sipariş akışı"
source_image: "satinalma-talep-akisi.png"
notation: swimlane
arrow_semantics: flow
language: tr
review_status: draft
overall_confidence: 0.9
canonical_graph: satinalma-talep-akisi.graph.json
counts: {nodes: 11, steps: 7, gateways: 3, edges: 12, lanes: 3}
---
# Satın alma talebi onay ve sipariş akışı

Talep eden bir satın alma talebi oluşturur, yönetici onaylar veya düzeltme ister; onaydan sonra satın alma teklif toplama ve bütçe kontrolünü paralel yürütür, ardından sipariş verir.

> Extracted from `satinalma-talep-akisi.png` (notation: swimlane, arrows read as: **flow**). Review status: **draft**. Source of truth: `satinalma-talep-akisi.graph.json`; this file is derived, do not hand-edit.

## 1. Summary

- Steps: 7 · gateways: 3 · lanes/participants: 3 · edges: 12
- Start: `baslangic` Talep Başla
- End: `bitis` Bitiş
- First steps (entry): `talep-olustur` Satın alma talebi oluştur
- Decision gateways: 1 · parallel gateways: 2 · loops: 1
- Inferred (not drawn): 0 node(s), 0 edge(s) · low-confidence (<0.6) nodes: 0 · open questions: 1

## 2. Participants

| id | label | kind | parent |
|---|---|---|---|
| `talep-eden` | Talep Eden | lane | - |
| `yonetici` | Yönetici | lane | - |
| `satin-alma` | Satın Alma | lane | - |

## 3. Steps and elements

| id | label | type | participant | confidence | status |
|---|---|---|---|---|---|
| `baslangic` | Talep Başla | start | Talep Eden | 0.95 | observed |
| `talep-olustur` | Satın alma talebi oluştur | task | Talep Eden | 0.95 | observed |
| `talep-duzelt` | Talebi düzelt | task | Talep Eden | 0.95 | observed |
| `talep-incele` | Talebi incele | task | Yönetici | 0.95 | observed |
| `onay-karari` | Onaylandı mı? | xor_gateway | Yönetici | 0.95 | observed |
| `paralel-bolme` | *none* | and_gateway | Satın Alma | 0.95 | observed |
| `teklif-topla` | Teklif topla | task | Satın Alma | 0.95 | observed |
| `butce-kontrol` | Bütçe kontrolü yap | task | Satın Alma | 0.95 | observed |
| `paralel-birlesme` | *none* | and_gateway | Satın Alma | 0.95 | observed |
| `siparis-ver` | Sipariş ver | task | Satın Alma | 0.95 | observed |
| `bitis` | Bitiş | end | Satın Alma | 0.95 | observed |

## 4. Control flow

Edges exactly as drawn (`source -> target`).

| id | from | to | type | condition / label | default | status |
|---|---|---|---|---|---|---|
| `e01` | `baslangic` | `talep-olustur` | sequence | - |  | observed |
| `e02` | `talep-olustur` | `talep-incele` | sequence | - |  | observed |
| `e03` | `talep-incele` | `onay-karari` | sequence | - |  | observed |
| `e04` | `onay-karari` | `paralel-bolme` | sequence | Evet |  | observed |
| `e05` | `onay-karari` | `talep-duzelt` | sequence | Hayır |  | observed |
| `e06` | `talep-duzelt` | `talep-incele` | sequence | - |  | observed |
| `e07` | `paralel-bolme` | `teklif-topla` | sequence | - |  | observed |
| `e08` | `paralel-bolme` | `butce-kontrol` | sequence | - |  | observed |
| `e09` | `teklif-topla` | `paralel-birlesme` | sequence | - |  | observed |
| `e10` | `butce-kontrol` | `paralel-birlesme` | sequence | - |  | observed |
| `e11` | `paralel-birlesme` | `siparis-ver` | sequence | - |  | observed |
| `e12` | `siparis-ver` | `bitis` | sequence | - |  | observed |

## 5. Task dependencies (derived)

A step may start only after its dependencies are satisfied. `ALL of` = parallel join (every one required). `ANY one of` = exclusive merge (exactly one branch arrives). Conditions come from decision branches.

| step | depends on | participant |
|---|---|---|
| `talep-olustur` Satın alma talebi oluştur | `baslangic` Talep Başla | Talep Eden |
| `talep-duzelt` Talebi düzelt | `talep-incele` Talebi incele [if: Hayır] | Talep Eden |
| `talep-incele` Talebi incele | `talep-olustur` Satın alma talebi oluştur<br>`talep-duzelt` Talebi düzelt | Yönetici |
| `teklif-topla` Teklif topla | `talep-incele` Talebi incele [if: Evet] | Satın Alma |
| `butce-kontrol` Bütçe kontrolü yap | `talep-incele` Talebi incele [if: Evet] | Satın Alma |
| `siparis-ver` Sipariş ver | ALL of: `teklif-topla` Teklif topla, `butce-kontrol` Bütçe kontrolü yap | Satın Alma |
| `bitis` Bitiş | `siparis-ver` Sipariş ver | Satın Alma |

## 6. Decision points

### `onay-karari` Onaylandı mı? (xor_gateway)

- if Evet -> `paralel-bolme` (AND)
- if Hayır -> `talep-duzelt` Talebi düzelt

## 7. Parallelism

- `paralel-bolme` forks into: `teklif-topla` Teklif topla, `butce-kontrol` Bütçe kontrolü yap

## 8. Loops and rework

- `talep-incele` -> `onay-karari` -> `talep-duzelt` -> `talep-incele`

## 9. Execution paths (up to 25, simple paths)

1. Talep Başla -> Satın alma talebi oluştur -> Talebi incele -> [Evet] (AND) -> Teklif topla -> Sipariş ver -> Bitiş
2. Talep Başla -> Satın alma talebi oluştur -> Talebi incele -> [Evet] (AND) -> Bütçe kontrolü yap -> Sipariş ver -> Bitiş
3. Talep Başla -> Satın alma talebi oluştur -> Talebi incele -> [Hayır] Talebi düzelt -> (loops back to `talep-incele`)

## 10. Review queue

Resolve these before treating the specification as `reviewed`.

| id | severity | about | question | candidates |
|---|---|---|---|---|
| q1 | minor | e05 | 'Hayır' etiketi düzeltme dalına mı ait? Etiket okun üstünde değil, elmasın altında duruyor. | Hayır -> Talebi düzelt (varsayılan okuma); Etiket başka bir okun |

## 11. Ontology mapping

- Vocabulary: `assets/ontology/workflow-vocabulary.ttl` (prefix `wfo:`), aligned to PKO (`pko:Procedure`, `pko:Step`, `pko:hasStep`, `pko:nextStep`), P-Plan (`p-plan:Step`, `p-plan:isPrecededBy`) and PROV-O (`prov:Agent`).
- Instance data: `satinalma-talep-akisi.ttl`. Every drawn arrow is also reified as a `wfo:Transition` so conditions are queryable.
- Derived relations: `wfo:precedes`, `wfo:dependsOn` (step-level, gateways collapsed), `wfo:performedBy` (lane), `wfo:reads` / `wfo:writes` (data edges).

## 12. How an agent should use this document

1. Treat section 5 as the dependency contract: do not schedule or reason about a step before its dependencies.
2. Honor `ALL of` / `ANY one of` and branch conditions literally; they come from gateway types, not guesses.
3. Anything in section 10 is unconfirmed. Ask the process owner or escalate instead of assuming; never fill gaps silently.
4. For exact ids, types and edge semantics, read the canonical JSON graph, not this prose.
