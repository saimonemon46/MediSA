# # # medical_triage_agent/
# # # │
# # # ├── app.py
# # # │
# # # ├── config/
# # # │   ├── settings.py
# # # │   └── groq_config.py
# # # │
# # # ├── data/
# # # │   ├── doctors.csv
# # # │   ├── diseases.csv
# # # │   ├── severity_weight.csv
# # # │   └── symptoms.csv
# # # │
# # # ├── agents/
# # # │   ├── triage_graph.py
# # # │   ├── conversation_agent.py
# # # │   ├── decision_agent.py
# # # │
# # # ├── services/
# # # │   ├── symptom_extractor.py
# # # │   ├── question_generator.py
# # # │   ├── severity_engine.py
# # # │   ├── doctor_service.py
# # # │
# # # ├── prompts/
# # # │   ├── followup_prompt.txt
# # # │   └── decision_prompt.txt
# # # │
# # # ├── utils/
# # # │   ├── csv_loader.py
# # # │   └── logger.py
# # # │
# # # └── README.md



# # START
# #  │
# #  ▼
# # Ask opening symptom question
# #  │
# #  ▼
# # Extract symptom(s)
# #  │
# #  ▼
# # Interactive Follow-up Loop
# #  │   ├─ LLM decides next best question
# #  │   ├─ Extract new symptoms
# #  │   ├─ Update severity score
# #  │   └─ Check stop condition
# #  │
# #  ▼
# # Severity Classification
# #  │
# #  ▼
# # Decision
# #  ├─ Low  → Basic advice → Ask doctor info
# #  ├─ Medium → Ask doctor info
# #  └─ High → Emergency prompt
# #  │
# #  ▼
# # Doctor lookup OR Emergency info
# #  │
# #  ▼
# # END



###################### app.py

# Purpose: Entry point

# Initializes graph

# Starts conversation loop

# Passes user input to LangGraph

# Nothing else. If this file grows, you failed.

######################################################## config/
################################ settings.py

### Severity thresholds

### Max follow-up limit

### Emergency numbers per country

# Hard rules belong here, not scattered in code.

#################################### groq_config.py

### API key loading

### Model selection

### Temperature, max tokens

# LLM config should never be hardcoded inside agents.

################################################# agents/
##################################### triage_graph.py

## Purpose: LangGraph orchestration

## Defines nodes

## Defines edges

## Controls state transitions

## No business logic. Just wiring.

#####################################conversation_agent.py

# Purpose: Runs the interactive symptom interview

# Calls LLM for questions

# Appends conversation history

# Stops when told to stop

# This agent does NOT calculate severity.

##################################### decision_agent.py

# Purpose: Rule-based routing

# Takes severity + state

# Decides:

# low / medium / high

# next node

# No LLM guessing here. Deterministic only.

######################################################################### services/
##################################### symptom_extractor.py

# Purpose: Convert raw text → known symptoms

# Keyword matching

# Synonym handling

# Fuzzy match if needed

# This keeps hallucinations from polluting severity.

##################################### question_generator.py

# Purpose: Ask the next best question

# Inputs:

# Collected symptoms

# Severity so far

# Conversation history

# Output:

# One focused follow-up question

# This uses the LLM, but with strict instructions.

##################################### severity_engine.py

# Purpose: Math, not magic

# Loads severity_weight.csv

# Computes score

# Assigns severity level

# If this ever calls an LLM, you’ve lost the plot.

##################################### doctor_service.py

# Purpose: Doctor lookup

# Filter by location

# Filter by speciality / concentration

# Format response

# No LLM required. CSV ≠ creativity.

######################################################################### prompts/
##################################### followup_prompt.txt

# Controls how the LLM asks questions:

# One question only

# No diagnosis

# No advice

# No medicine

# Prompts change more than code. Keep them separate.

##################################### decision_prompt.txt

# Optional if you want LLM-assisted reasoning, but:

# Output must be structured

# Never allowed to override severity rules

# ########################################################################utils/
##################################### csv_loader.py

# Loads CSV once

# Caches dataframes

# Avoids reloading on every turn

# Performance matters even in demos.

##################################### logger.py

# Logs decisions

# Logs severity score

# Logs emergency triggers

# This saves you during debugging and thesis defense.