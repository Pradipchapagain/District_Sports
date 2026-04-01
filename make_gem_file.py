import os

# यो फाइलमा सबै कोड गएर सेभ हुन्छ
output_filename = "Kabaddi_Project_For_Gemini.txt"

# कुन-कुन फोल्डर र फाइल तान्ने हो?
target_folders = ["pages", "utils"]
target_files = ["Home.py", "database.py", "config.py", "requirements.txt"]

def create_context_file():
    with open(output_filename, "w", encoding="utf-8") as outfile:
        outfile.write("यस फाइलमा Kabaddi Live TV प्रोजेक्टका मुख्य कोडहरू छन्।\n")
        outfile.write("="*60 + "\n\n")

        # १. बाहिरका मुख्य फाइलहरू (Root Files) तान्ने
        for file in target_files:
            if os.path.exists(file):
                outfile.write(f"--- File: {file} ---\n")
                try:
                    with open(file, "r", encoding="utf-8") as infile:
                        outfile.write(infile.read())
                    outfile.write("\n\n")
                    print(f"✅ {file} जोडियो।")
                except Exception as e:
                    print(f"❌ {file} पढ्न समस्या भयो: {e}")
            else:
                print(f"⚠️ {file} भेटिएन!")

        # २. फोल्डर भित्रका सबै फाइलहरू तान्ने
        for folder in target_folders:
            if os.path.exists(folder):
                for root, dirs, files in os.walk(folder):
                    for file in files:
                        # पाइथन (.py) फाइलहरू मात्र तान्ने (फोटो वा अरू नतान्ने)
                        if file.endswith(".py"):
                            filepath = os.path.join(root, file)
                            # विन्डोजको ब्याकस्ल्यास (\) लाई फरवार्ड स्ल्यास (/) बनाउने (हेर्न सजिलो हुन्छ)
                            clean_filepath = filepath.replace("\\", "/") 
                            
                            outfile.write(f"--- File: {clean_filepath} ---\n")
                            try:
                                with open(filepath, "r", encoding="utf-8") as infile:
                                    outfile.write(infile.read())
                                outfile.write("\n\n")
                                print(f"✅ {clean_filepath} जोडियो।")
                            except Exception as e:
                                print(f"❌ {clean_filepath} पढ्न समस्या भयो: {e}")
            else:
                print(f"⚠️ {folder} फोल्डर भेटिएन!")

    print(f"\n🎉 बधाई छ! सबै कोडहरू '{output_filename}' मा तयार भयो।")

if __name__ == "__main__":
    create_context_file()