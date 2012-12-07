import sys
import re
global output
output = ''

# user configurations #
FILE_NAME = '/auto/gsg-users/thumpal/xpp/design/script/packet_class/svplextend.sv'
ORIGINAL_CLASS_FILE_NAME = "/auto/gsg-users/thumpal/xpp/design/script/svpl/svpl_top_class.sv"

# automation marker strings #
premarker = "//AUTOMATION MARKER - BEGIN "
termination_marker = "//AUTOMATION MARKER - END "
postmarker = "\n"

# maximum number of times to try manipulating distributions to cover a bin (when feedback is active) #
number_of_tries = 8



# global variables #
global counter
counter = 0


################################################################################
#PYTHON FUNCTIONS
################################################################################


################################################################################
#
#Purpose:  Creates a coverpoint for enumeration variables.
#Variables: var_name - enumeration variable's name.
#           values - list of enumeration values to create bins for.
#
################################################################################
def CreateEnumCov(var_name, values):
    global output
    for x, val in enumerate(values):
        output += "\t" + var_name + "_" + str(x) + ": coverpoint " + var_name + " { "
        output += "bins " + var_name + "_" + str(x) + " = {" + str(x) + "}; "
        output += "}\n"


################################################################################
#
#Purpose:  Creates a coverpoint for numerical variables.
#Variables: variable_str - the variable's name that is begin covered.
#           bin1_name - the coverpoint name and the bin name.
#           myborders - list of values to create bins for.  If the list entry is a list 
#               then a range will be created.
#
################################################################################
def CreateCovpoint(variable_str, bin1_name, myborders):
    global output
    for x in range(len(myborders)):
        if (isinstance(myborders[x], list)):
            output += "\t" + bin1_name + "_" + str(x) + ": coverpoint " + variable_str + " { "
            output += "bins " + bin1_name + "_" + str(x) + " = {[" + str(myborders[x][0]) + ":" \
                      + str(myborders[x][1]) + "]}; }\n"
        else:
            output += "\t" + bin1_name + "_" + str(x) + ": coverpoint " + variable_str + " { "
            output += "bins " + bin1_name + "_" + str(x) + " = {" + str(myborders[x]) + "}; "
            output += "}\n"


################################################################################
#
#Purpose:  Creates a cross between two coverpoints.
#Variables: cov1_str - coverpoint/bin name.
#           len1 - number of coverpoints (bins).
#           cov2_str - coverpoint/bin name for variable 2.
#           len2 - number of coverpoints (bins) for variable 2.
#
################################################################################
def CreateCross(cov1_str, len1, cov2_str, len2):
    global output
    for i in range(len1):
        for j in range(len2):
            output += "\t" + cov1_str + "_" + str(i) + "X" + cov2_str + "_" + str(j) + \
                ": cross " + cov1_str + "_" + str(i) + ", " + cov2_str + "_" + str(j) + ";\n"


################################################################################
#
#Purpose:  Creates a cross between two variables.
#Variables: var - main variable to cross.
#           arr_cross_variables - list of variables to cross the main variable with.
#
################################################################################
def CreateCrosses(var, arr_cross_variables):
    global output
    for i, v in enumerate(arr_cross_variables):
        CreateCross(var.bin, var.len, v.bin, v.len)


################################################################################
#
#Purpose:  Creates a manual feedback loop to make sure all the bins were covered
#               when in feedback mode.
#Variables: all - list of all variables
#           cover_group_name - covergroup name.
#
################################################################################
def FeedbackCoverpointCoverage(all, cover_group_name):
    global counter
    global output
    output += "\t\t\tif (0) begin end\n"
    for i, var in enumerate(all):
        for j in range(var.len):
            output += "\t\t\telse if ((this." + cover_group_name + "." + var.bin + "_" + \
                      str(j) + ".get_coverage() < 100) && (this.try_counter[" + str(counter) + \
                      "] > 0)) begin\n"
            output += "\t\t\t\tthis.w8_" + var.bin + "[" + str(j) + "] = 100000000;\n"
            output += "\t\t\t\tthis.try_counter[" + str(counter) + "]--;\n"
            counter += 1
            output += "\t\t\tend\n"


################################################################################
#
#Purpose:  Creates a manual feedback loop to make sure crosses were covered.
#               Active only when in feedback mode.  Specifically for variables
#               that can be assigned during the same cycle.
#Variables: var1 - the first variable that was crossed.
#           var2 - the second variable that was crossed.
#           cover_group_name - covergroup name.
#
################################################################################
def FeedbackCrossNowXNow(var1, var2, cover_group_name):
    global counter
    global output
    for i in range(var1.len):
        for j in range(var2.len):
            output += "\t\t\telse if ((this." + cover_group_name + "." + var1.bin + "_" + \
                      str(i) + "X" + var2.bin + "_" + str(j) + ".get_coverage() < 100) && " + \
                      "(this.try_counter[" + str(counter) + "] > 0)) begin\n"
            output += "\t\t\t\tthis.try_counter[" + str(counter) + "]--;\n"
            counter += 1
            output += "\t\t\t\tthis.w8_" + var1.weight + "[" + str(i) + "] = 100000000;\n"
            output += "\t\t\t\tthis.w8_" + var2.weight + "[" + str(j) + "] = 100000000;\n"
            output += "\t\t\tend\n"


################################################################################
#
#Purpose:  Creates a manual feedback loop to make sure crosses were covered.
#               Active only when in feedback mode.  Specifically for variables
#               that are assigned during the seperate cycles.
#Variables: var1 - the first variable that was crossed. Will be assigned next cycle.
#           var2 - the second variable that was crossed. Will be assigned this cycle.
#           cover_group_name - covergroup name.
#
################################################################################
def FeedbackCrossNowXPrev(var1, var2, cover_group_name):
    global counter
    global output
    for i in range(var1.len):
        for j in range(var2.len):
            output += "\t\t\telse if ((this." + cover_group_name + "." + var1.bin + "_" + \
                      str(i) + "X" + var2.bin + "_" + str(j) + ".get_coverage() < 100) && " + \
                      "(this.try_counter[" + str(counter) + "] > 0)) begin\n"
            output += "\t\t\t\tthis.try_counter[" + str(counter) + "]--;\n"
            counter += 1
            output += "\t\t\t\tthis.nextw8_" + var1.weight + "[" + str(i) + "] = 100000000;\n"
            output += "\t\t\t\tthis.w8_" + var2.weight + "[" + str(j) + "] = 100000000;\n"
            output += "\t\t\t\tthis.isbusy = 1;\n"
            output += "\t\t\tend\n"


################################################################################
#
#Purpose:  Creates many FeedbackCrossNowXPrev calls.
#Variables: var1 - the main variable that was crossed. 
#           arr_var2 - a list of variables to cross against the main.
#           cover_group_name - covergroup name.
#
################################################################################
def FeedbackManyCrossNowXPrev(var1, arr_var2, cover_group_name):
    global output
    for var2 in arr_var2:
        FeedbackCrossNowXPrev(var1, var2, cover_group_name)






################################################################################
# Purpose:  Checks if a file exists, gets the lines of the markers.  Use in
#           conjunction with SwitchMarkerDomain.
# Input:    markers - input, name of the markers to look for or create
#           myfilename - input, file path
# Output:   f_exists -  output, did the file exist
#           starts -    output, list of start marker lines
#           ends -      output, list of end marker lines
#           lines -     output, file contents
################################################################################
def GetFileMarkers(markers, myfilename):
    starts = range(len(markers))
    starts = [-1 for x in starts]
    ends = starts[:]
    lines = []
    try:
        f = open(myfilename,'r')
        lines = f.readlines()
        f_exists = 1
        f.close()
    except IOError:
        f_exists = 0

    if f_exists == 1:
        for i, line in enumerate(lines):
            for j, mark in enumerate(markers):
                if line == (premarker + mark + postmarker):
                    starts[j] = i
                    break
                elif line == (termination_marker + mark + postmarker):
                    ends[j] = i
                    break
        for mylist in [ends, starts]:
            for i in mylist:
                if (i <= -1):
                    print "ERROR: Couldn't find automation marker in file, exiting:", myfilename
                    sys.exit()
    return (f_exists, starts, ends, lines)


################################################################################
# Purpose:  Use to switch between automation markers, preserves userfeed file
#           contains.
# Input:    index1 - input, integer, index of the automation marker being
#               switched from
#           index2 - input, integer, index of the automation marker begin
#               switched to
#
################################################################################
def SwitchMarkerDomain(index1, index2):
    global output
    if (index1 >= 0):
        output += termination_marker + markers[index1] + postmarker
    if f_exists == 0:
        output += "\n"
        output += "\n"
        output += "\n"
    else:
        if (index1 >= 0) and (index2 >= 0):
            for line in lines[ends[index1]+1:starts[index2]]:
                output += line
        elif (index2 < 0):
            for line in lines[ends[index1]+1:]:
                output += line
        else:
            for line in lines[0:starts[index2]]:
                output += line
    if (index2 >= 0):
        output += premarker + markers[index2] + postmarker


################################################################################
#Output for DECLARATION
################################################################################
def Declaration():
    global output
    output += "class " + class_name + " extends " + org_class_name + ";\n"
    output += "\n"
    output += "int isbusy;\n"
    output += "int isfeedbackactive;\n"
    for i, v in enumerate(all):
        if v.sv_var_type == "":
            continue
        else:
            output += v.sv_var_type + " " + v.name + ";\n"
    for i, v in enumerate(declare_vars):
        output += "int w8_" + v.bin + "[" + str(v.len-1) + ":0];\n"
    output += "int try_counter[];\n"
    for i, v in enumerate(declare_vars):
        output += "int nextw8_" + v.bin + "[" + str(v.len-1) + ":0];\n"


################################################################################
#Output for COVERPOINT
################################################################################
def Coverpoint():
    global output
    output += "covergroup " + cover_group_name + ";\n"
    # create coverpoints #
    for v in all:
        if (v.type == 2):
            CreateEnumCov(v.name, v.values)
        if (v.type == 1):
            CreateCovpoint(v.name, v.bin, v.values)


################################################################################
#Output for DISTRIBUTION
################################################################################
def Distribution():
    global output
    for k, v in enumerate(dist_vars):
        if v.constraint_name == "":
            output += "constraint constraint_" + str(k) + " {\n"
        else:
            output += "constraint " + v.constraint_name + " {\n"
        output += "\t" + v.name + " dist {\n"
        for i, val in enumerate(v.values):
            if (isinstance(val, list)):
                if (i == len(v.values)-1) and (len(dist_vars) == k+1):
                    output += "\t\t[" + str(val[0]) + ":" + str(val[1]) + "] :/ w8_" + v.bin + "[" + str(i) + "]\n"
                else:
                    output += "\t\t[" + str(val[0]) + ":" + str(val[1]) + "] :/ w8_" + v.bin + "[" + str(i) + "],\n"
            else:
                if (i == len(v.values)-1) and (len(dist_vars) == k+1):
                    output += "\t\t" + str(val) + " := w8_" + v.bin + "[" + str(i) + "]\n"
                else:
                    output += "\t\t" + str(val) + " := w8_" + v.bin + "[" + str(i) + "],\n"
        output += "\t};\n"
        output += "}\n"



################################################################################
#Output for FEEDBACK
################################################################################
def PreFeedback():
    global output
    output += "function void pre_randomize();\n"
    output += "\tint i;\n"
    output += "\tsuper.pre_randomize();\n"
    for i, v in enumerate(all):
        if v.cycle == 2:
            output += "\tthis." + v.name + " = this." + v.prev_member + ";\n"
    # start feedback, busy ifs #
    output += "\tif (this.isfeedbackactive == 1) begin\n"
    for i, v in enumerate(declare_vars):
        output += "\t\tthis.w8_" + v.bin + " = '{" + str(v.len) + "{1}};\n"
    output += "\t\tif (this.isbusy <= 0) begin\n"
    output += "\n"

def PostFeedback():
    global output
    # end coverage if #
    output += "\t\t\telse begin\n"
    output += "\t\t\t\t$display($get_coverage(" + cover_group_name + "));\n"
    output += "\t\t\t\t$finish();\n"
    output += "\t\t\tend\n"
    output += "\t\tend\n"
    output += "\t\telse begin\t\t//isbusy == 1\n"
    output += "\t\t\tthis.isbusy--;\n"

    # 'next' weight variables are assigned to 'now' weight variables #
    for i, v in enumerate(declare_vars):
        output += "\t\t\tfor (i=0; i<$size(nextw8_" + v.bin + "); i++) begin\n"
        output += "\t\t\t\tif (nextw8_" + v.bin + "[i] > -1) begin\n"
        output += "\t\t\t\t\tw8_" + v.bin + "[i] = nextw8_" + v.bin + "[i];\n"
        output += "\t\t\t\t\tnextw8_" + v.bin + "[i] = -1;\n"
        output += "\t\t\t\tend\n"
        output += "\t\t\tend\n"

    # end ifs #
    output += "\t\tend\n"
    output += "\tend\n"
    output += "endfunction\n"


################################################################################
#Output for POSTRANDOMIZE
################################################################################
def PostRandomize():
    global output
    output += "function void post_randomize();\n"
    output += "\tsuper.post_randomize();\n"
    output += "\t" + cover_group_name + ".sample();\n"
    output += "endfunction\n"


################################################################################
#Output for INITIALIZATION
################################################################################
def DeleteFirstWordInGroup1(matchobj):
    return re.sub(matchobj.group(1), "", matchobj.group())

def Initialize():
    global output
    if new_function_mobj:
        isnew = 1
        output += new_function_mobj.group() + "\n"
    else:
        isnew = 0
        output += "function new ();\n"
    output += "\tint i;\n"
    if isnew == 1:
        new_contents = re.sub(r"\[.*?\]", "", new_function_mobj.group(1))
        new_contents = re.sub(r"([a-zA-Z0-9_]+[ \t]+)[a-zA-Z0-9_]+[ \t,)]", DeleteFirstWordInGroup1, new_contents)
        output += "\tsuper.new" + new_contents + "\n"
    # initialize weights to 1, 'next' weights to -1 #
    for i, v in enumerate(init_vars):
        output += "\tthis.w8_" + v.bin + " = '{" + str(v.len) + "{1}};\n"
    for i, v in enumerate(init_vars):
        output += "\tthis.nextw8_" + v.bin + " = '{" + str(v.len) + "{-1}};\n"
    output += "\tthis.try_counter = new[" + str(counter) + "];\n"
    output += "\tfor(i=0; i<" + str(counter) + "; i++) begin\n"
    output += "\t\tthis.try_counter[i] = " + str(number_of_tries) + ";\n"
    output += "\tend\n"
    output += "\tthis.isbusy = 0;\n"
    output += "\tthis.isfeedbackactive = 0;\n"
    output += "\t" + cover_group_name + " = new;\n"
    output += "endfunction\n"
    output += "\n"
    output += "\n"
    output += "endclass\n"


################################################################################
#
#Variable classes
#
################################################################################
class var_enum:
    def __init__ (self, name, values, weight, sv_var_type="", cycle=1, prev_member="", constraint_name = ""):
        self.name = name
        self.type = 2
        self.len = len(values)
        self.values = values
        self.weight = weight
        self.bin = name
        self.cycle = cycle
        self.sv_var_type = sv_var_type
        self.prev_member = prev_member
        self.constraint_name = constraint_name
        #self.member = member 

class var_num:
    def __init__ (self, name, values, bin, weight, sv_var_type="", cycle=1, prev_member="", constraint_name = ""):
        self.name = name        #name of variable to cover
#types:
    #1 - numerical
    #2 - enum
        self.type = 1           #what type is the variable:  numerical, enum, etc...
        self.len = len(values)  #length of values list
        self.values = values    #list of numerical values - can be a list of individual values, or a list of lists (ranges).
        self.bin = bin          #string, coverpoint name, also bin name
        self.weight = weight    #string, coverpoint weight to change (when not forcing)
        self.sv_var_type = sv_var_type  #string, system verilog variable type, specify only if the variable doesn't 
                                        #already exist in super class (e.g. "int", "logic", "PktTypeTb")
        self.cycle = cycle              #int, cycle which variable is sampled (1 for present cycle, 2 for previous cycle)
        self.prev_member = prev_member  #string, if cycle = 2, the name of the present cycle signal (e.g. "length":  this.prevlength = this.length)
        self.constraint_name = constraint_name  #string, name of constraint, set only if applicable.  An automatic name will be generated otherwise.

#we don't want this
        #self.member = member    #variable name to change when forcing (probably wont use).


################################################################################
#Python variable definitions
#
#Below we are covering packet lengths, packet types, previous packet lengths,
#and previous packet types.  Lengths include powers of two, +/- 1 the powers of
#two, and the ranges inbetween.
#
#Packet types are an enumeration.
#
################################################################################
mylengths1 = [64,128,256,512,1024,2048,4096,9216]
mylengths2 = [x-1 for x in mylengths1[1:]]
mylengths3 = [x+1 for x in mylengths1[0:-1]]
mylengths4 = [[mylengths1[i]+2, mylengths1[i+1]-2] for i in range(len(mylengths1[0:-1]))]
lengths = []
for mylist in [mylengths1, mylengths2, mylengths3, mylengths4]:
    for i in mylist:
        lengths.append(i)
v1 = var_num("frame_length", lengths, "border", "border")
v2 = var_num("prevlength", lengths, "pborder", "border", sv_var_type="int", cycle=2, prev_member="frame_length")
v3 = var_enum("manual_pkt_type", range(22), "manual_pkt_type", sv_var_type="rand bit [5:0]") 
v4 = var_enum("prevpkt_type", range(22), "manual_pkt_type", sv_var_type="int", cycle=2, prev_member="manual_pkt_type")


#list of all the variables
all = [v1, v2, v3, v4]
#list of variables to automate distribution constraints for
dist_vars = [v1]
#list of variables to declare distribution weights for
declare_vars = [v1, v3]
#list of variables to automate initialization for
init_vars = [v1, v3]


cover_group_name = "CovPacket"
class_name = "MyPacket"

#look at original class, try to find class name, new function declaration
lines = []
try:
    f = open(ORIGINAL_CLASS_FILE_NAME,'r')
    lines = f.readlines()
    f_exists = 1
    f.close()
except IOError:
    f_exists = 0
    print "ERROR: Couldn't find file:", ORIGINAL_CLASS_FILE_NAME
    sys.exit()
for line in lines:
    class_name_mobj = re.search(r"^[ \t]*class[ \t]*([^ \n,;/\t.]+)", line)
    if class_name_mobj:
        org_class_name = class_name_mobj.group(1)
        break
if not (class_name_mobj):
    print "ERROR: Failed to find original class name!  Cannot extend."
    sys.exit()
for line in lines:
    new_function_mobj = re.search(r"[ \t]*function[ \t]+new[ \t]+(\(.*\)[ \t]*;)", line)
    if new_function_mobj:
        break


output = ""
markers = ["DECLARATION", "COVERPOINT", "DISTRIBUTION", "FEEDBACK", "POSTRANDOMIZE", "INITIALIZATION"]
f_exists, starts, ends, lines = GetFileMarkers(markers, FILE_NAME)
SwitchMarkerDomain(-1, 0)

# create declaration output #
Declaration()
SwitchMarkerDomain(0, 1)
Coverpoint()


# create crosses #
CreateCrosses(v1, [v2, v3])
CreateCrosses(v3, [v4])


output += "endgroup\n"
SwitchMarkerDomain(1, 2)
# create distribution output #
Distribution()
SwitchMarkerDomain(2, 3)
PreFeedback()


# create manual feedback for variables #
FeedbackCoverpointCoverage([v1, v3], cover_group_name)

# create manual feedback for crosses 'now cross now' #
FeedbackCrossNowXNow(v1, v3, cover_group_name)

# create manual feedback for crosses 'now cross previous' #
FeedbackCrossNowXPrev(v1, v2, cover_group_name)
FeedbackCrossNowXPrev(v3, v4, cover_group_name)


PostFeedback()
SwitchMarkerDomain(3, 4)
PostRandomize()
SwitchMarkerDomain(4, 5)
Initialize()
SwitchMarkerDomain(5, -1)

f = open(FILE_NAME, 'w')
f.write(output)
f.close()

