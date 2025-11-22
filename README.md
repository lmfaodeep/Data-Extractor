**HOW TO USE
1. Set your OPENAI_API_KEY in your local environment.
2. Add the file path to the program (for example: /mnt/data/yourfile.pdf).
3. Run your Python file normally.
4. The extracted data will be saved in your local folder as both CSV and XLSX formats.



-This project is an automated data-extraction system designed to convert unstructured documents such as PDFs, scanned files, and text-heavy reports into clean, structured CSV or Excel outputs using the OpenAI Responses API. The goal is to transform messy narrative documents into machine-ready tabular data with minimal manual intervention.

-The system works by uploading a source file (PDF, XLSX, or other formats) to the OpenAI API, sending a highly controlled prompt that instructs the model to output clean CSV rows, and then parsing that CSV into a formatted Excel sheet. Each extracted row follows a consistent schema:

-KEY - A canonical label representing the field
(examples: name, birth_date, birth_place, nationality, blood_group, current_job, employer, salary_current, certifications, demographic_marker, and more)

-VALUE - The smallest, most precise text snippet from the document that contains the actual information.

-COMMENTS - Usually empty, but may include helpful context such as ISO-formatted dates (iso:YYYY-MM-DD), emergency relevance, or short clarifications within 20 words.

-PAGE - The page number when identifiable, otherwise left blank.

-The system forces the AI to output strict CSV-only formatting, avoiding noise, markdown, or explanations. This ensures maximum reliability when converting the result into Excel.

-The project includes strong error handling:

-Automatic fallback when invalid file_id errors occur.

-Detection of locked Excel files and retry with timestamped filenames.

-Graceful handling of CSV parsing failures by saving raw output for debugging.

-Optional retry logic for rate limits, network issues, and long processing times.

-This pipeline is ideal for extracting structured data from resumes, reports, identity documents, profiles, and any text-based document where metadata needs to be converted into a clean table. By combining controlled AI parsing with consistent schema enforcement, the system reduces manual effort and improves data accuracy and consistency.
