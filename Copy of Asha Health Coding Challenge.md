# **Asha Health Coding Challenge: Build an AI Medical Scribe Web App**

## **Guidelines**

* You will have 24 hours from the time you receive this challenge to complete it.  
* The challenge is divided into three sections. The scope is intentionally broad, and some instructions may be deliberately ambiguous. This is to assess how you approach problem-solving and prioritize tasks.  
* The scope is large for a 24-hour timeframe—you are not expected to cover everything. We recommend getting bits and pieces working end-to-end so that you have something to show, even if you can’t get the full project complete.  
* Prioritize clean, maintainable code quality, architecture design, optimization for latency, and thoughtful trade-offs over trying to implement everything superficially.  
* Once your project is complete, push your code to a Git repository and include build and run instructions in the README. Additionally, provide a script that allows us to build and run the entire project with a single command.

## **Background**

Medical documentation is one of the most time-consuming aspects of healthcare delivery. Clinicians spend hours each day documenting patient encounters, often staying late to complete their notes. Your challenge is to build an AI medical scribe system that can significantly reduce this burden by automatically generating high-quality clinical notes from patient-provider conversations.

## **Task Overview**

Build a basic web app that can:

* Record a visit between a doctor and a patient upon the doctor tapping a start button.  
* Transcribe the visit (you may use a transcription API of your choice, Deepgram and Assembly AI are known to be good)  
* Use AI to produce a SOAP note once the visit is complete (please feel free to research what these clinical notes entail)

**Performance Requirements:**

* Your system should be able to handle 30-40 minute conversations efficiently. We recommend testing it on [this sample conversation from AWS](https://drive.google.com/file/d/1XAyddBAFUgJ9BX3RxISJswDjRXHlxJUe/view?usp=sharing).  
* You should implement strategies to minimize latency for both transcription and note generation \- clinicians would ideally want their SOAP note to finish generating within seconds after the visit completes.  
* You should implement techniques to make the AI more accurate, and ensure its outputs align with formats the clinician desires.

**Edge Cases (Bonus – we recommend trying to implement at least 1 of these):**

* How would you create a mapping between each line in the final SOAP note and the excerpts from the transcript from which it was inferred? (So that a physician could hover over that line and see where it came from, as they review the note for accuracy before they sign it)  
* Design a feedback loop that improves accuracy over time based on clinician edits  
* How would you handle medical conversations with multiple speakers (provider, patient, nurse, family member)?  
* How would your system manage poor audio quality or strong accents?

## **Evaluation Criteria**

Your solution will be evaluated based on:

* **Code Quality and Architecture**  
  * Clean, maintainable code with appropriate error handling  
  * Thoughtful architecture that separates concerns and scales well  
  * Efficient data structures and algorithms that minimize computational overhead  
* **Latency Optimization**  
  * Innovative approaches to reduce processing and generation time  
  * Effective utilization of parallel processing where appropriate  
  * Measurable performance improvements with increasing conversation length  
* **AI Accuracy and Relevance**  
  * Techniques you leverage to improve AI accuracy  
  * How you verify AI output  
  * How you ensure AI output is in desired format and style clinician wants  
* **User Experience**  
  * Intuitive interfaces that minimize clinician cognitive load  
  * Efficient correction mechanisms that learn from feedback  
  * Thoughtful integration with clinical workflow

## **Submission Requirements**

* Complete code repository with documentation  
* A working demo that showcases the end-to-end process (we recommend giving us instructions on how to run it and also recording a 2 minute Loom video)

Remember to focus on getting a working end-to-end solution first, then optimize for performance and accuracy. Good luck\!

