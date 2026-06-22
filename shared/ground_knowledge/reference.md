# Data Layer Reference

**Purpose:** Document the domain grounding, supporting evidence, and rationale behind selected signals, derived features, and proxy failure definitions.

```
Signal
  (KIT Automotive OBD-II Dataset)
    │
    ▼
Feature
  (Derived Features)
    │
    ▼  [Fault Signature Knowledge]
Proxy Failure
  (failure_signatures)
```

## 1. Raw Signals

Document the meaning and expected behaviour of original OBD-II variables.

For each signal include:

* Physical meaning
* Unit
* Expected relationships & Expected operating behaviour
* Supporting source

### 1.1 Engine Coolant Temperature

**Physical Meaning:** Reflects the overall thermal state of the engine.

**Unit:** °C

**Expected Relationships:** 

* Higher engine load → gradual temperature increase.
* After warm-up → temperature should stabilise.
s
**Source:** Bosch Automotive Handbook

### 1.2 To be con

...


## 2. Derived Features

Document engineered features and why they are introduced.

For each feature include:

* Inputs
* Formula
* Intended signal & Supporting rationale
* Supporting source

### 2.1 coolant_slope

**Inputs:** coolant_temp

**Formula:** ΔTemp / ΔTime

**Intended Signal:** Heat accumulation rate
    Persistent temperature increase may indicate cooling inefficiency.

**Source:** Cherdo et al. (2023)

### 2.2 To be con

...


# 3. Proxy Failure Definitions

Document proxy failures and supporting evidence.

For each proxy include:

* Supporting signals/features
* Expected abnormal pattern & Rationale
* Supporting source
* Confidence

### 3.1 cooling_degradation

**Supporting Features**
    coolant_temp
    coolant_slope

**Expected Pattern:** Temperature remains elevated after warm-up.
    Sustained overheating may indicate reduced cooling performance.

**Evidence**
    EDA plots
    Feature statisticss

**Confidence:** Medium

### 3.2 To be con

...



## 4. References

### Literature

...

### Automotive Resources

...

### Dataset Notes

...


