# Title: Recognizing Psychological Defense Mechanisms in Supportive Conversations

## Keywords
psychological defense mechanisms, supportive dialogue, utterance classification, conversational context, mental health NLP

## TL;DR
How can the psychological defense mechanism expressed by an utterance be recognized from the utterance and the supportive conversation around it? Investigate this question on the PsyDefConv corpus.

## Abstract
Psychological defense mechanisms are unconscious strategies people use to cope with distress, and they leave traces in language: denial, projection, rationalization and related mechanisms shape how a speaker responds to what was said before. The PsyDefConv corpus makes this observable at scale. It contains supportive conversations split into turns, and every target utterance is annotated with one of eight defense-mechanism categories or with "none", so that recognizing a mechanism is a nine-way labelling problem over an utterance that sits inside a dialogue. The corpus comes with a fixed dialogue-level split into training and evaluation records; performance is reported as macro-F1 over the eight defense categories, computed by the corpus's official scorer on the evaluation records. Work at this venue asks what kind of evidence identifies a mechanism: is it carried by the wording of the utterance itself, by its relation to the preceding turns, by speaker roles, or by patterns that only appear across a whole conversation? Contributions typically compare two to four materially different approaches under matched conditions and argue from the comparison. The computational setting is modest and self-contained: studies run offline on CPU with the Python standard library, numpy, pandas, scipy and scikit-learn, without pretrained models or downloads, which keeps the focus on the linguistic question rather than on scale.
