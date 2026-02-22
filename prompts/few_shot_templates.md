# Few-Shot Translation Templates

Templates para construir prompts de traducción con ejemplos recuperados por RAG.

## Template: Ayoreo → Español

```
Traducí el siguiente texto de Ayoreo a Español.

Ejemplos de traducciones correctas:
  Ayoreo: {example_1_ayo}
  Español: {example_1_es}

  Ayoreo: {example_2_ayo}
  Español: {example_2_es}

Vocabulario relevante:
  {word_1} = {definition_1}
  {word_2} = {definition_2}

Texto a traducir (Ayoreo):
  {input_text}

Traducción (Español):
```

## Template: Español → Ayoreo

```
Traducí el siguiente texto de Español a Ayoreo.

Ejemplos de traducciones correctas:
  Español: {example_1_es}
  Ayoreo: {example_1_ayo}

  Español: {example_2_es}
  Ayoreo: {example_2_ayo}

Vocabulario relevante:
  {word_1} = {definition_1}

Texto a traducir (Español):
  {input_text}

Traducción (Ayoreo):
```
