from os import listdir
from os.path import isfile, isdir, join
from os import getcwd
from pickle import TRUE
from os import system
import re   # Python RegEx expressions library

DEBUG_SESSION = False

HEADER_FILE = 1
SOURCE_FILE = 2
ALL_FILES   = 3

CMD_CFLOW_POSIX    = "cflow --number --brief --format=posix "
CMD_CFLOW_RVRS     = "cflow --number --brief --reverse "
CMD_CFLOW_BASIC    = "cflow --number -d2 --reverse "
OUTPUT_FILE_NAME   = "cflow_output" 
OUTPUT_FILE_EXT    = ".txt" 

CFLOW_FORMAT_POSIX = 0
CFLOW_FORMAT_RVRS  = 1
CFLOW_FORMAT_BSC   = 2

current_dir = getcwd()   # Get current directory for project folders
project_dir = ""

# Create dictionary for header files, key will store header file name
# value will store list that have included headers
header_files = {}   
source_files = []
extern_funcs = set({})    # Functions that declared global scope (We declare this variable as set due to prevent duplication)
called_funcs = set({})    # Functions that used in this file (We declare this variable as set due to prevent duplication)
header_files_loc = []
source_files_loc = []
struct_head = "---"
extensions = ["c", "h"]   # File extensions that desired to be found (C and Header files at now)

def app_GetFileNamesofDirectory(path):
    files = []
    files = [file for file in listdir(path) if isfile(join(path, file))]
    return files


def app_GetFolderNamesofDirectory(path):
    folders = []
    folders = [folder for folder in listdir(path) if isdir(join(path, folder))]
    return folders


def app_IsAnySubFolder(path):
    if len(app_GetFolderNamesofDirectory(path)) != 0:
        return True
    return False


def app_PrintDirectoryTree(path, struct_h):
    folders = []
    folders = app_GetFolderNamesofDirectory(path)

    if len(folders) != 0:   # If any subfolder exists
        for folder in folders:
            if "." not in folder:   # Do not apply the process into hidden files
                print(struct_h + folder)   # Complete folder path
                app_PrintDirectoryTree((path + "/" + folder), (struct_h + "---"))


def app_GetCFLowOutputFile(cflow_out):
    if cflow_out == CFLOW_FORMAT_POSIX:
        out = OUTPUT_FILE_NAME + "_posix" + OUTPUT_FILE_EXT
    elif cflow_out == CFLOW_FORMAT_BSC:
        out = OUTPUT_FILE_NAME + "_basic" + OUTPUT_FILE_EXT
    else:
        out = OUTPUT_FILE_NAME + "_rvrs" + OUTPUT_FILE_EXT
    return out


def app_CreateCFlowOutputFile(cflow_out):
    out = app_GetCFLowOutputFile(cflow_out)
    cmd = "touch " + out        # Create new cflow output file (If a file exists with this name it will not create new one)
    system(cmd)
    cmd = 'echo "" > ' + out    # Clear all content of the cflow output file
    system(cmd)
    return (out)


def app_RunCFlowCmd(cflow_out):
    if cflow_out == CFLOW_FORMAT_POSIX:
        cmd = CMD_CFLOW_POSIX
    elif cflow_out == CFLOW_FORMAT_BSC:
        cmd = CMD_CFLOW_BASIC
    else:   # CFLOW_RVRS
        cmd = CMD_CFLOW_RVRS
    out = app_GetCFLowOutputFile(cflow_out)

    for src_index in range(len(source_files_loc)):
        cmd += "" + source_files_loc[src_index] + " "

    cmd += " >> " + out
    system(cmd)


def app_PrintProjectFolderTree(path, struct_h, regex):
    folders = []
    files = []
    folders = app_GetFolderNamesofDirectory(path)
    files = app_GetFileNamesofDirectory(path)

    if len(folders) != 0:   # If any subfolder exists
        for folder in folders:
            if "." not in folder:   # Do not apply the process into hidden files
                print(struct_h + folder)   # Complete folder path
                app_PrintProjectFolderTree((path + "/" + folder), (struct_h + "---"), regex)
    
    if len(files) != 0:     # If any file exists,
        for file in files:
            if regex != "":
                if re.findall(regex, str(file)):
                    print(struct_h + file)
            else:
                print(struct_h + file)


def app_SetProjectSourceAndHeaderFiles(path, regex):
    folders = []
    files = []
    folders = app_GetFolderNamesofDirectory(path)
    files = app_GetFileNamesofDirectory(path)

    if len(folders) != 0:   # If any subfolder exists
        for folder in folders:
            if "." not in folder:   # Do not apply the process into hidden files
                app_SetProjectSourceAndHeaderFiles((path + "/" + folder), regex)
    
    if len(files) != 0:     # If any file exists,
        for file in files:
            if regex != "":
                if re.findall("\.c$", str(file)):
                    source_files_loc.append(path + "/" + file)
                    file = file[:(re.search('\.c$', file).start())]
                    source_files.append(file)
                if re.findall("\.h$", str(file)):
                    file = file[:(re.search('\.h$', file).start())]
                    if file.upper() not in list(header_files.keys()):   # Prevent same file names in search tree
                        header_files_loc.append(path + "/" + file + ".h")
                        header_files[file.upper()] = []   # We do not want to header file research case sensistive


# Set all header files (Store Header file names in key and included files in values)
def app_SetIncludedHeaderFilesForProject():
    hd_file_name = ""
    print("=======" + str(len(header_files)))
    
    if len(header_files_loc) == 0:
        app_ErrorHandler(2)
    else:
        for index in range(len(header_files_loc)):
            hd_file_name = str(list(header_files.keys())[index])
            header_files[hd_file_name] = app_GetHeadersFromFile(header_files_loc[index])
        

def app_FindAllExternFunctionsOfFile(header_file_loc):
    ext_funcs = []      # Functions that declared as extern in this file
    rgx_rule = "^ *?extern .*\(.*\);"

    with open(header_file_loc, encoding="Latin-1") as file:   # utf8 (NOK), Latin-1 (OK)
        Lines = file.readlines()
        temp_line = ""

        for line in Lines:
            line_str = line.strip()
            if re.findall(rgx_rule, str(line_str)):
                temp_line = line_str[:re.search(".*\(", line_str).end()-1]   # Add -1 in order to ignore "(" paranthesis
                temp_line = temp_line[((re.search("extern.*?[a-zA-Z]", temp_line).end())-1):]
                temp_line = temp_line[(re.search(".* .*?", temp_line).end()):]
                ext_funcs.append(temp_line)
    
    return ext_funcs


def app_SetAllExternFunctionsOfProject():
    if len(header_files_loc) == 0:
        app_ErrorHandler(2)
    else:
        for index in range(len(header_files_loc)):
            extern_funcs.update(app_FindAllExternFunctionsOfFile(header_files_loc[index]))


def app_CreateAndGetRegExRule(extension):
    rgx = ""
    # Create Regex rule
    for index in range(len(extension)):
        rgx += "\." + str(extension[index]) + "$"    # End with rule ($)
        if index != len(extension)-1:
            rgx += "|"
    if DEBUG_SESSION is True:
        print("\nRegex Rule: " + rgx + "\n")
    return rgx


def app_FindProjectFolderPath():
    global project_dir
    project_folder = app_GetFolderNamesofDirectory(current_dir)

    if DEBUG_SESSION == True:
        print("Project Directory: ", current_dir)
        
    if len(project_folder) == 1: 
        project_dir = current_dir + "/" + str(project_folder[0])
        return True
    elif len(project_folder) == 0: 
        app_ErrorHandler(0)
    else:
        app_ErrorHandler(1)
    return False


def app_GetHeadersFromFile(path):
    line_num = 0
    headers = []

    with open(path, encoding="Latin-1") as file:   # utf8 (NOK), Latin-1 (OK)
        Lines = file.readlines()
        temp_line = ""

        for line in Lines:
            line_str = line.strip()
            line_num += 1
            if ("#include" in line_str) and (re.findall('\.h[>|"]$', str(line_str))):
                temp_line = line_str[re.search('#include .*?[<|"]', line_str).end():]
                temp_line = temp_line[:(re.search('\.h[>|"]', temp_line).start())]
                headers.append(temp_line.upper())

    return headers


def app_GetAllFunctionsFromSourceFile(path, source_file="", cflow_format=CFLOW_FORMAT_RVRS):
    # This method has been written based on POSIX format GNU cflow outputs for source(C) files
    # cflow --number --brief --format=posix <file_name.c> >> output.txt
    # Ex. cflow --number --brief --format=posix trk_LevelManager.c >> output.txt
    defined_funcs = []       # Functions that defined in this file
    tmp_called_funcs = set({})   # Functions that used in this file (We declare this variable as set due to prevent duplication)
    cal_rgx_rule = "\d.*<>"
    if cflow_format == CFLOW_FORMAT_POSIX:
        def_rgx_rule = ": .*, <.*"      # ": .*, <"
        def_rgx_rule = def_rgx_rule + source_file + "\.c.*" 

    with open(path, encoding="Latin-1") as file:   # utf8 (NOK), Latin-1 (OK)
        Lines = file.readlines()
        temp_line = ""

        for line in Lines:
            line_str = line.strip()
            # cflow --format=posix
            if cflow_format == CFLOW_FORMAT_POSIX:
                if re.findall(def_rgx_rule, str(line_str)):
                    temp_line = line_str[:re.search(def_rgx_rule, line_str).start()]
                    if re.findall("([ ]{2,})" , temp_line):   # If whitespace is less than 2, it shows just definition of the function (Not used in this scope) 
                        temp_line = temp_line[((re.search("\d.*?[a-zA-Z]", temp_line).end())-1):]
                        called_funcs.add(temp_line)   # Add functions to global called function list
                    else:
                        temp_line = temp_line[((re.search("\d.*?[a-zA-Z]", temp_line).end())-1):]
                    defined_funcs.append(temp_line)
                if re.findall(cal_rgx_rule, str(line_str)):
                    temp_line = line_str[((re.search("\d.*?[a-zA-Z]", line_str).end())-1):]
                    temp_line = temp_line[:re.search(": <>.*", temp_line).start()]
                    tmp_called_funcs.add(temp_line)
                    called_funcs.add(temp_line)   # Add functions to global called function list
            # cflow --reverse
            elif cflow_format == CFLOW_FORMAT_RVRS:
                #if re.findall("\d.*\(\)(:|$)", str(line_str)):
                if re.findall("\d.*\(\):", str(line_str)):
                    temp_line = line_str[((re.search("\d.*?[a-zA-Z]", line_str).end())-1):]
                    temp_line = temp_line[:re.search("\(\).*", temp_line).start()]
                    tmp_called_funcs.add(temp_line)
                    called_funcs.add(temp_line)   # Add functions to global called function list
                elif re.findall("\d.*\(\)(:| |$).*:$", str(line_str)):    
                    temp_line = line_str[((re.search("\d.*?[a-zA-Z]", line_str).end())-1):]
                    temp_line = temp_line[:re.search("\(\).*", temp_line).start()]
                    tmp_called_funcs.add(temp_line)
                    called_funcs.add(temp_line)   # Add functions to global called function list
            # cflow -d2 --brief
            elif cflow_format == CFLOW_FORMAT_BSC:
                if re.findall("\d.*\(\).*>?.*:$", str(line_str)):
                    temp_line = line_str[:(re.search("\(\).*>?.*:$", line_str).start())]
                    temp_line = temp_line[((re.search("\d.*?[a-zA-Z]", temp_line).end())-1):]
                    tmp_called_funcs.add(temp_line)
                    called_funcs.add(temp_line)   # Add functions to global called function list


    if DEBUG_SESSION is True:
        print("============= Defined Functions by {0}.c File =============".format(source_file))
        for funs in defined_funcs:
            print(funs)
        print("\n============= Called Functions by {0}.c File  =============".format(source_file))
        for funs in tmp_called_funcs:
            print(funs)
    return tmp_called_funcs    # We just need to called functions by this source file


# file_loc_list: source/header file locations list
# file_type: HEADER_FILE or SOURCE_FILE file type
def app_PrintUnnecessaryHeaderFileUsage(file_type):
    if file_type == SOURCE_FILE:  file_loc_list = source_files_loc
    elif file_type == HEADER_FILE:  file_loc_list = header_files_loc   # HEADER_FILE
    else:  # ALL_FILES
        app_PrintUnnecessaryHeaderFileUsage(SOURCE_FILE)
        file_type = HEADER_FILE
        file_loc_list = header_files_loc

    for index in range(len(file_loc_list)):      # For each source file in the project
        if file_type == HEADER_FILE:
            print("\n============ Unnecessary Header file usage in {0}.h File ============".format(str(list(header_files.keys())[index]).lower()))
        else:
            print("\n============ Unnecessary Header file usage in {0}.c File ============".format(source_files[index]))
        headers = app_GetHeadersFromFile(file_loc_list[index])
        duplicated_hdrs = {"None"}  # Set data type is generally used to store data without repetition
        for header in headers:      # For each included header files
            if header in (header_files.keys()):
                # Some included header files may not be contained in scope
                for hdr_ctrl in header_files[header.upper()]:   # For each header files that already included in header
                    if hdr_ctrl.upper() in headers:
                        duplicated_hdrs.add(hdr_ctrl)
        app_PrintDuplicatedHeaderFiles(duplicated_hdrs)     
    
    print("\n===========================\n")       


def app_PrintAllHeadersOfFile(file_type):
    if file_type == SOURCE_FILE:
        file_loc_list = source_files_loc
        header_list = source_files
    elif file_type == HEADER_FILE:  
        file_loc_list = header_files_loc   # HEADER_FILE
        header_list = list(header_files.keys())
    else:  # ALL_FILES
        app_PrintAllHeadersOfFile(SOURCE_FILE)
        file_type = HEADER_FILE
        file_loc_list = header_files_loc
        header_list = list(header_files.keys())

    if file_type == SOURCE_FILE:
        print("\n\n=========== Source File Headers ===========")
    else:
        print("\n\n=========== Header File Headers ===========")
    for index in range(len(file_loc_list)):
        if file_type == SOURCE_FILE:
            print("\n{0}.c File Headers:".format(str(header_list[index])))
        else:
            print("\n{0}.h File Headers:".format(str(header_list[index]).lower()))
        headers = app_GetHeadersFromFile(file_loc_list[index])
        for header in headers:
            if header != header_list[index]:
                print("------{0}".format(header.lower()))
    
    print("\n============================================================================================================")      


def app_PrintDuplicatedHeaderFiles(duplicated_hdrs):
    for header in duplicated_hdrs:
        if len(duplicated_hdrs) == 1: print("None")
        elif header != "None":
            print(str(header.lower()) + ".h")


def app_ApplicationInit():  
    tmp_called_funcs_posix = set({})
    tmp_called_funcs_rvrs = set({})
    # Create ReGex rule for given file extensions
    regex = app_CreateAndGetRegExRule(extensions)
    # Append header and source files into file lists for stated project
    app_SetProjectSourceAndHeaderFiles(project_dir, regex)

    # Set all header files (Store Header file names in key and included files in values)
    app_SetIncludedHeaderFilesForProject()

    # Set all global (extern) functions (Store extern function names in set variable in order to prevent usage of same function name)
    app_SetAllExternFunctionsOfProject()

    #if DEBUG_SESSION is True:
    print("\n============= Project Folder Tree =============")
    app_PrintProjectFolderTree(project_dir, struct_head, "")     # Without regex expression
    print("\n============================================================================================================")     
    app_PrintAllHeadersOfFile(ALL_FILES)
    print("Total Source File number of the project: {0}".format(len(source_files)))
    print("Total Header File number of the project: {0}".format(len(header_files)))

    # Print unnecessary header file usage in stated project according to sources files
    app_PrintUnnecessaryHeaderFileUsage(ALL_FILES)

    # CFLOW OUTPUT SESSION    
    app_CreateCFlowOutputFile(CFLOW_FORMAT_POSIX)
    app_RunCFlowCmd(CFLOW_FORMAT_POSIX)

    app_CreateCFlowOutputFile(CFLOW_FORMAT_RVRS)
    app_RunCFlowCmd(CFLOW_FORMAT_RVRS)

    app_CreateCFlowOutputFile(CFLOW_FORMAT_BSC)
    app_RunCFlowCmd(CFLOW_FORMAT_BSC)

    tmp_called_funcs_posix = app_GetAllFunctionsFromSourceFile("cflow_output_posix.txt", cflow_format=CFLOW_FORMAT_POSIX)
    tmp_called_funcs_rvrs = app_GetAllFunctionsFromSourceFile("cflow_output_rvrs.txt", cflow_format=CFLOW_FORMAT_RVRS)

    print("\n============= ALL EXTERN FUNCTIONS DECLARED IN PROJECT =============")
    for ext_func in extern_funcs:
        print("{0}".format(ext_func))

    print("\n============= ALL USED (CALLED) FUNCTIONS IN PROJECT =============")
    for cll_func in tmp_called_funcs_rvrs:
        print("{0}".format(cll_func))

    print("\n============= NEVER USED (CALLED) GLOBAL FUNCTIONS IN PROJECT =============")
    for ext_func in extern_funcs:
        if ext_func not in tmp_called_funcs_rvrs:
            print("{0} Function is never used in any other file for this project (OR function reference)".format(ext_func))
    #for ext_func in extern_funcs:
    #    if ext_func not in tmp_called_funcs_posix:
    #        print("{0} Function is never used in any other file for this project (OR function reference)".format(ext_func))
    #print("=======================================")
            

def main():
    if app_FindProjectFolderPath() != False:
        app_ApplicationInit()
        # print("\nDo you want to clear all of the unnecessary header file duplications?[Y/N]")
        key = input()


def app_ErrorHandler(err):
    if err == 0:
        print("ER00: There is no project folder in stated directory")
    elif err == 1:
        print("ER01: There are more project folders than expected!")
    elif err == 2:
        print("ER02: There is no header files in stated project directory")

if __name__ == "__main__":
    main()