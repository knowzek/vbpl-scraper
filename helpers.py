import json, requests, os

def wJson(jsonFile, filePath):
    with open(filePath, 'w', encoding='utf-8') as jsonWriter:
        json.dump(jsonFile, jsonWriter, ensure_ascii=False, indent=4)

def rJson(filePath):
    with open(filePath, encoding='utf-8') as jsonReader:
        return json.load(jsonReader)
    
def newFolderCreate(folder_name,dPath):
    complete_path = os.path.join(dPath, folder_name)
    if not (os.path.exists(complete_path) and os.path.isdir(complete_path)):
        new_directory = os.path.join(dPath, folder_name)
        os.makedirs(new_directory)