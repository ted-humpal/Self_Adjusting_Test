'''
Created by:  Theodore Humpal  8/8/2008
'''

import sys
import re
from optparse import OptionParser
from autodefines import *

global output

#NOTE: issues are marked by '#MARK' 


################################################################################
#                           User Configurations
################################################################################

FILE = "/auto/gsg-users/thumpal/xpp/design/script/XppDpm4Ge2XgWrap.sv"  #file with DUT declaration
DEFINES_FILE = "/auto/gsg-users/thumpal/xpp/design/script/XppDpm4Ge2XgWrapDefines.vh"   #file with interface declarations
PARITY_REG_FILE = "/auto/gsg-users/thumpal/xpp/design/script/ParityRegisterDefinesDPM.txt"  #file with the list of Parity Registers.  For parity injection tasks.

tb_path_name = './tb/'
test_path_name = './test/'
bus_model_path_name = './busmodel/'
monitor_path_name = './monitor/'
reference_model_path_name = './ref/'

#   file names will eventually be ...   #
#tb_file_name = tb_path_name + module_name + '_mytb.sv'
#test_file_name = test_path_name + module_name + '_mytest.sv'
#busmodel_file_name = bus_model_path_name + module_name + '_mybus.sv'
#monitor_file_name = monitor_path_name + module_name + '_mymonitor.sv'
#reference_model_file_name = reference_model_path_name + module_name + '_myreference_model.sv'


# tb naming options #
bus_model_name = "my_bus_model"
monitor_name = "mon"
reference_model_name = "my_ref"


##############
#CLOCK OPTIONS
##############
# If these strings are in a signal that is detected as a clock, the "clock" status will be nullified. (case ignored) #
    #assume 'cnt' and 'count' mean signal isn't a clock
    #assume 'rst' and 'reset' mean signal isn't a clock 
clks_to_skip = ["cnt", "count", "rst", "reset", "step", "stp", "tst"]

# If these strings are in a signal that is detected as a clock, the given number is associated as half its period. (case ignored) #
#MARK - I made up some of these
clk_periods = {"sys":"750", "vfe":"1960", "tx":"1334", "cpu":"7519"}

##############
#INTERFACE PARITY SIGNAL OPTIONS
##############
# Should there be random parity errors in interface parity signals? #
is_parity_errors = 1
# 1 chance out of ? #
par_err_chance_string = "200"


##############
#AUTOMATION MARKER STRINGS
##############
turnmarkerson = 1
premarker = "//AUTOMATION MARKER - BEGIN "
termination_marker = "//AUTOMATION MARKER - END "
postmarker = "\n"









################################################################################
#                           Important signal lists
################################################################################
global dut_signals, tb_signals, clk_signals, rst_signals, ref_signals, ref_in_signals 
global mon_signals, assert_signals, bus_signals, bus_in_signals
global cim_in_signal, cim_out_signal, parity_signals, modport_outputs


# lines of signal declarations #
dut_signals = []        #lines for declaring the DUT
tb_signals = []         #lines for declaring the signals needed within the testbench
clk_signals = []        #clock signals used for declaring the clock generators
rst_signals = []        #reset signals for declaring the reset initializers
ref_signals = []        #lines for declaring the Reference Model
ref_in_signals = []     #lines for instantiating the Reference Model
mon_in_signals = []     #lines for instantiating the Monitor
mon_signals = []        #lines for declaring the Monitor
assert_signals = []     #lines for asserting in the Monitor
bus_signals = []        #lines for declaring the bus model signals
bus_in_signals = []     #lines for instantiating the Bus Model

# Individual signals #
cim_in_signal = []      #may contain cimRingIn
cim_out_signal = []     #may contain cimRingOut
parity_signals = []     #may contain parity signals of the interfaces to the DUT
                        #[0] - parity signal name, [1] - parity reference signal, [2] - interface name
modport_outputs = []    #holds outputs of the bus model
                        #[0] - bus output signal name, [1] - modport name that the output belongs to


################################################################################
#                           Command line options
################################################################################

parser = OptionParser()

# main file to parse #
parser.add_option("-f", "--file", dest="file",
                  help=".sv FILE to parse", default=FILE)

# file with interface definitions #
parser.add_option("-i", "--include", dest="defines",
                  help=".vh FILE to get interface information", default=DEFINES_FILE)

# file with list of registers for parity fault injection #
parser.add_option("-p", "--parity", dest="parity_file",
                  help=".vh FILE to get interface information", default=PARITY_REG_FILE)

global options
(options, args) = parser.parse_args()


################################################################################
#                           Regular expressions
################################################################################

# finding/replacing ',' in reversed strings #
comma_re = re.compile(r"^\n*[ \t]*,")
comma_replace_re = re.compile(r",")

# finding/replacing 'input', 'output' #
input_re = re.compile(r"[ \t]*input")
input_replace_re = re.compile(r"input[ \t]*")
output_re = re.compile(r"[ \t]*output")
output_replace_re = re.compile(r"output[ \t]*")

# finding/replacing 'logic' #
logic_re = re.compile(r"^[ \t]*logic")
logic_replace_re = re.compile(r"logic")

# finding/replacing 'wire' #
wire_re = re.compile(r"^[ \t]*wire")
wire_replace_re = re.compile(r"wire")

# finding/replacing 'reg' #
reg_re = re.compile(r"^[ \t]*reg")
reg_replace_re = re.compile(r"reg")

# finding/spliting off comments #
comments_startofline_re = re.compile(r"^[ \t]*/[/*]")
comments_re = re.compile(r"/[/*]")

# replacing everything in brackets (inclusive of brackets) #
bracket_contents_re = re.compile(r"\[.*?\]")

# finding/replacing structures in signal declarations, after input,  #
# and braket contents are gone. #
#                      (space... word... space... word...) #
structure_re = re.compile(r"[ \t]*[^ \n,;/\t]+[ \t]+[^ \n,;/\t]+") 
structure_replace_re = re.compile(r"[^ \n,;/\t]+") 




################################################################################
#Regular expression FUNCTIONS           (for replacement)
################################################################################

# replace group1 with spaces #
def replace_group1_with_spaces(matchobj):
    string = ''
    for x in xrange(len(matchobj.group(1))):
        string += ' '
    return re.sub(matchobj.group(1), string, matchobj.group(), 1)

# add '_ref,' to the match #
def add_ref_comma(matchobj):
    return matchobj.group() + "_ref,"

# add '_ref' to the first group #
def add_ref_to_group1(matchobj):
    return re.sub(matchobj.group(1), matchobj.group(1) + "_ref", matchobj.group(), 1)
def add_ref_to_group1_twice(matchobj):
    return re.sub(matchobj.group(1), matchobj.group(1) + "_ref", matchobj.group(), 2)

# add '_ref' to the first group #
def add_ref_comma_to_group1(matchobj):
    return re.sub(matchobj.group(1), matchobj.group(1) + "_ref,", matchobj.group(), 1)

# replace group1 with output #
def replace_group1_with_output(matchobj):
    return re.sub(matchobj.group(1), "output", matchobj.group(), 1)







################################################################################
#Other Funtions
################################################################################

################################################################################
#Purpose: pass in a line, output a list of the parsed words.  Parsing between 
#           spaces, parentheses, commas, semicolons.
#Input: define_line - line to be parsed
#Output: words - list of seperated strings deemed to be 'words'
################################################################################
def LineToWords(define_line):
    words = []
    mod_lines = define_line.split(" ")
    for group in mod_lines:
        tempgroup = group.split("\t")
        for part in tempgroup:
            words.append(part)
    i = 0
    for word in words:
        word = re.sub(r"\(", "", word)
        word = re.sub(r"\n", "", word)
        word = re.sub(r"\)", "", word)
        word = re.sub(r"\;", "", word)
        words[i] = re.sub(r",", "", word)
        i += 1
    try:
        while (1):
            words.remove('')
    except ValueError:
        #do nothing
        j = 0
    return words


################################################################################
#Purpose: Decide whether a signal is a clock and what its timing delay is.
#Input:  sig - a clk string (a signal name).
#Output:
#   skip - If creating a clock generator for the signal should be skipped.
#   txt_number - The string form of half the clock period.
#   issys - If it's the sys clock.
################################################################################
def ClksToSkip(sig):
    skip = 0
    txt_number = "0"
    issys = 0
    for aclk in clks_to_skip:
        if re.search(aclk, sig, re.I):
            skip = 1

    found = 0
    for aclk in clk_periods.keys():
        if re.search(aclk, sig, re.I):
#MARK - below is a 'sys' assumption
            if re.search("sys", sig, re.I):
                issys = 1
            txt_number = clk_periods[aclk]
            found = 1
            break
    if found == 0:
        # couldn't identify clk, will not generate a clk like signal #
        print "WARNING: Could not identify clock, omitting clk generator - " + sig
        skip = 1
    return [skip, txt_number, issys]
 

################################################################################
# Purpose:  Get all needed information about the interface
# Input:    define_lines - interface definition file lines
#           interface_name_mobj - interface name match object
#           modport_name_mobj - modport name match object
################################################################################
def FindModportDirections(define_lines, interface_name_mobj, modport_name_mobj):
    global modport_outputs
    global parity_signals
    isinterface = 0
    isinmodport = 0
    endmodport = 0
    for define_line in define_lines:
        words = []
        define_line = re.sub(r"/[/*].*", "", define_line) 
        if endmodport == 1:
            isinmodport = 0
            endmodport = 0
        if re.search(r"^[ \t]*interface[ \t]*"+interface_name_mobj.group(1), define_line):
            isinterface = 1
        if re.search(r"endinterface", define_line):
            isinterface = 0
        if isinterface == 1:
            if re.search(r"\)", define_line):
                endmodport = 1
            if re.search(r"modport[ \t]+" + modport_name_mobj.group(1) + "[ \t]+", define_line):
                # we're at the beginning of the relevant modport declaration #
                isinmodport = 1
                words = LineToWords(words, define_line)
                type = 0                        # type:  0 - unknown, 1 - input, 2 - output #
                if len(words) > 2:
                    for word in words[2:]:        
                        if word == 'input':
                            type = 1
                            continue
                        elif word == 'output':
                            type = 2
                            continue
                        if type == 2:
                            # this should be an output signal, grab it #
                            modport_outputs.append([word, modport_name_mobj.group(1)])
            elif isinmodport == 1:
                # we're somewhere in the middle of the modport declaration #
                words = LineToWords(words, define_line)
                type = 0                        # type:  0 - unknown, 1 - input, 2 - output #
                for word in words:        
                    if word == 'input':
                        type = 1
                        continue
                    elif word == 'output':
                        type = 2
                        continue
                    if type == 2:
                        # this should be an output signal, grab it #
                        modport_outputs.append([word, modport_name_mobj.group(1)])




# search the specified include file for interface definition #
# try to get the corresponding interface #
################################################################################
# Purpose:  Get all needed information about the interface using the 
#           specified include file.
# Input:    line - original line declaring the interface in the DUT
#           options - options parser (contains file name to parse)
#           interface_declaration_mobj - interface declaration match object
# Output:   modport_name_mobj - modport name match object
################################################################################
def GetInterfaceInformation(line, options, interface_declaration_mobj):
    global parity_signals
    global bus_signals
    interface_name_mobj = re.search(r"[ \t]*([^ \n,;/\t.]+).[^ \n,;/\t.]+[ \t]+([^ \n,;/\t.]+)", line)
    defines_file = open(options.defines, 'r')
    define_lines = defines_file.readlines()
    isinterface = 0
    isinmodport = 0
    endmodport = 0
    found_interface = 0
    line_for_bus = line
    for define_line in define_lines:
        if endmodport == 1:
            isinmodport = 0
            endmodport = 0
        if re.search(r"^[ \t]*interface[ \t]*"+interface_name_mobj.group(1), define_line):
            found_interface = 1
            isinterface = 1
        if re.search(r"endinterface", define_line):
            isinterface = 0
        if re.search(r"[ \t]*modport", define_line):
            isinmodport = 1
        if re.search(r"\)", define_line):
            endmodport = 1

        # get parity signals #
        # look at signals inside the valid interface, check if it's a parity signal, (make sure we're not inside a modport) #
        if isinmodport == 0 and isinterface == 1:
            # delete bracket contents and eol comments #
            parity_line = bracket_contents_re.sub("", define_line) 
            parity_line = re.sub(r"/[/*].*", "", parity_line) 
#MARK
#assuming parity signals are in an interface only!
#MARK
#assuming string 'parity' will find the parity signals
            if re.search(r"parity", parity_line, re.I):
                parity_mobj = re.match(r"[ \t]*[^ \n,;/\t.]+[ \t]+([^ \n,;/\t.]+)", parity_line)
                if parity_mobj:
                    parity_signal_name = parity_mobj.group(1)
                    # We have the parity signal.  Now we need to find the associated signal group in the interface. #

#MARK
#assuming signal name minus "parity" is the associated bus signal
                    parity_search_name = re.sub(r"[Pp][Aa][Rr][Ii][Tt][Yy]", "", parity_mobj.group(1), 1)
                    myisinterface = 0
                    myisinmodport = 0
                    myendmodport = 0
                    found = 0
                    for mydefine_line in define_lines:
                        if myendmodport == 1:
                            myisinmodport = 0
                            myendmodport = 0
                        if re.search(r"^[ \t]*interface[ \t]*"+interface_name_mobj.group(1), mydefine_line):
                            myisinterface = 1
                        if re.search(r"endinterface", mydefine_line):
                            myisinterface = 0
                        if re.search(r"[ \t]*modport", mydefine_line):
                            myisinmodport = 1
                        if re.search(r"\)", mydefine_line):
                            myendmodport = 1

                        if isinmodport == 0 and isinterface == 1:
                            parity_line = bracket_contents_re.sub("", mydefine_line) 
                            parity_line = re.sub(r"/[/*].*", "", parity_line) 
                            
                            if re.search(parity_search_name, parity_line, re.I):
                                my_parity_mobj = re.match(r"[ \t]*[^ \n,;/\t.]+[ \t]+([^ \n,;/\t.]+)", parity_line)
                                if my_parity_mobj:
                                    found = 1
                                    # we now have a parity signal and the bus it is checking! #
                                    parity_signals.append([parity_mobj.group(1), my_parity_mobj.group(1), interface_name_mobj.group(2)])
                                    break
                    if found == 0:
                        print "ERROR:  parity signal found, could not match it to a signal"




        # Find a modport name that is not declared in the module, guess the name declaration for the bus model. #
        if isinterface == 1:    # currently looking inside relevant interface #
            modport_name_mobj = re.search(r"modport[ \t]+([^ \n,;/\t.]+)", define_line)
            if modport_name_mobj:
                if interface_declaration_mobj.group(1) <> modport_name_mobj.group(1):
                    line_for_bus = re.sub(r"\.[^ \n,;/\t.]+", "." + modport_name_mobj.group(1), line_for_bus, 1)
                    bus_signals.append(line_for_bus)
                    break

    # now find the inputs and outputs of that modport #
    FindModportDirections(define_lines, interface_name_mobj, modport_name_mobj)
    if (found_interface == 0):
        print "ERROR: Never found interface in interface definition file."
        sys.exit()
    return (modport_name_mobj)


################################################################################
# Purpose:  Checks if a file exists, gets the lines of the markers.  Use in
#           conjunction with SwitchMarkerDomain.
# Input:    markers - input, name of the markers to look for or create
#           myfilename - input, file path
# Output:   f_exists -  output, (1 or 0) did the file exist
#           starts -    output, list of ints, start marker lines
#           ends -      output, list of ints, end marker lines
#           lines -     output, list of strings, file contents
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
#           contents.
# Input:    index1 - input, integer, index of the automation marker being
#               switched from
#           index2 - input, integer, index of the automation marker begin
#               switched to
#
################################################################################
def SwitchMarkerDomain(index1, index2):
    global output
    if (index1 >= 0):
        if (turnmarkerson == 1):
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
        if (turnmarkerson == 1):
            output += premarker + markers[index2] + postmarker


################################################################################
#Start parsing main file
################################################################################

# open file #
f = open(options.file, 'r')
lines = f.readlines()
found = 0
isduplicate = 0
module_line_num = 0

#MARK
    #should use regular expressions instead
# Find module declaration #
for line in lines:
    words = line.split(" ")
    if words[0] == "module":
        module_name = words[1]
        found = 1
        break
    module_line_num = module_line_num + 1
if found == 0:
    print "ERROR: module declaration could not be found!"
    sys.exit(0)


# Collect signals that the testbench needs to simulate #
print "Starting: " + module_name

for line in lines[module_line_num+1:]:
    skip = 0
    isclk = 0
    iscimringin = 0
    iscimringout = 0
    isrst = 0
    words = []

    # construct words array.  (rid ourselves of spaces and tabs) #
    tempwords = line.split(" ")
    for almost_word in tempwords:
        temparr = almost_word.split("\t")
        for word in temparr:
            words.append(word)
    try:
        while (1):
            words.remove('')
    except ValueError:
        # do nothing #
        j = 0

    # if line is a comment, flag a skip #
    if comments_startofline_re.match(line):
        skip = 1
    
    # if line is a newline, flag a skip #
    if words[0] == "\n":    # ignore newlines #
        skip = 1

    if skip == 0:   # is a signal #
        ################################################################################
        # We have a valid line in the module declaration.  Let's start parsing the signal.
        ################################################################################

        # split off any end of line comments #
        broken_line = comments_re.split(line,1)
        # Get rid of everything in [] #
        broken_line[0] = bracket_contents_re.sub("", broken_line[0]) 

#MARK
    #'clk', 'cimringin', 'cimringout', 'rst' assumptions
        # find special signals, ignoring case #
        if re.search("clk",broken_line[0],re.I) or re.search("clock",broken_line[0], re.I):
            isclk = 1
        elif re.search("cimringin",broken_line[0],re.I):
            iscimringin = 1
        elif re.search("cimringout",broken_line[0],re.I):
            iscimringout = 1
#MARK
    #'rst' is a dangerous search, will match words like 'first', 'burst', etc
        elif re.search("rst",broken_line[0],re.I) or re.search("reset",broken_line[0], re.I):
            isrst = 1

        dut_line = line
        tb_line = line

        # decide whether the line is an input, output, interface, or the end of the module declaration #
        if 'input' in words:            # try to find an input signal #
            isinput = 1
            ref_signals.append(line)
            if iscimringin <> 1 and iscimringout <> 1:
                if isclk == 1 or isrst == 1:
                    bus_line = line
                else:
                    bus_line = re.sub(r"^[ \t]*(input)", replace_group1_with_output, line, 1)
                    # replace 'logic' with bit #
                    if re.search(r"[ \t]logic[ \t]", bus_line):
                        bus_line = re.sub(r"logic", "bit", bus_line, 1)
                bus_signals.append(bus_line)
            if input_re.match(dut_line):
                dut_line = input_replace_re.sub("", dut_line, 1)
            if input_re.match(tb_line):
                tb_line = input_replace_re.sub("", tb_line, 1)

            # replace 'logic' and 'wire' with 'bit' for inputs #
            if logic_re.match(tb_line):
                tb_line = logic_replace_re.sub("bit", tb_line, 1)
            if wire_re.match(tb_line):
                tb_line = wire_replace_re.sub("bit", tb_line, 1)

        elif 'output' in words:         # try to find an output signal #
            isinput = 0
            isclk = 0
            ref_signals.append(line)

            # delete 'output' from signal for dut and tb #
            if output_re.match(dut_line):
                dut_line = output_replace_re.sub("", dut_line, 1)
            if output_re.match(tb_line):
                tb_line = output_replace_re.sub("", tb_line, 1)

            # use 'logic' instead of 'wire' or 'reg' #
            if reg_re.match(tb_line):
                tb_line = reg_replace_re.sub("logic", tb_line, 1)
            if wire_re.match(tb_line):
                tb_line = wire_replace_re.sub("logic", tb_line, 1)

            # get outputs, modify, add to monitor declaration #
            if output_re.match(line):
                mon_line = re.sub("output", "input", line, 1)
                if re.match(r"^[ \t]*input[ \t]*reg", mon_line):
                    mon_line = reg_replace_re.sub("logic", mon_line, 1)
                if re.match(r"^[ \t]*input[ \t]*wire", mon_line):
                    mon_line = wire_replace_re.sub("logic", mon_line, 1)
                mon_signals.append(mon_line)

        elif re.search(r"^[ \t]*\);", line):    # end of module declaration #
            ref_signals.append(line)
            #print "broke"
            break

        else:                           # interface #
            isinput = 2
            # get interface.modport #
            interface_declaration_mobj = re.search(r"^[ \t]*[^ \n,;/\t.]+\.([^ \n,;/\t.]+)", line)

            # add '_ref' to needed signals #
            if re.search(r"[^/,]*,", line):
                                       # space, interface  .   modport    space   interface_name #
                line_for_ref = re.sub(r"^[ \t]*[^ \n,;/\t.]+\.[^ \n,;/\t.]+[ \t]+([^ \n,;/\t.]+)", add_ref_to_group1, line, 1)
            else:
                line_for_ref = re.sub(r"^[ \t]*[^ \n,;/\t.]+\.[^ \n,;/\t.]+[ \t]+([^ \n,;/\t.]+)", add_ref_comma_to_group1, line, 1)
            ref_signals.append(line_for_ref)
            line_for_ref = line_for_ref
            
            # get rid of '.modport_name', replace with spaces #
            if interface_declaration_mobj:
                line_for_ref = re.sub(r"(\.[^ \n,;/\t.]+)", replace_group1_with_spaces, line, 1)
            ref_signals.append(line_for_ref)


            # search the specified include file for interface definition #
            # try to get the corresponding interface #
            modport_name_mobj = GetInterfaceInformation(line, options, interface_declaration_mobj)


            line_for_mon = re.sub(r"\.[^ \n,;/\t.]+", "." + modport_name_mobj.group(1), line, 1)
            if re.search(r"[^/,]*,", line_for_mon):
                                       # space, interface  .   modport    space   interface_name #
                line_for_mon = re.sub(r"^[ \t]*[^ \n,;/\t.]+\.[^ \n,;/\t.]+[ \t]+([^ \n,;/\t.]+)", add_ref_to_group1, line_for_mon, 1)
            else:
                line_for_mon = re.sub(r"^[ \t]*[^ \n,;/\t.]+\.[^ \n,;/\t.]+[ \t]+([^ \n,;/\t.]+)", add_ref_comma_to_group1, line_for_mon, 1)
            mon_signals.append(line_for_mon)
            mon_signals.append(line_for_ref)
     

        # find implicily declared wires, and add logic/bit #
        templine = bracket_contents_re.sub("", tb_line) 
        if not re.search(r"^[ \t]*[^ \t\n,;/]+[ \t]+[^ \t\n,;/]", templine):
            word = re.search(r"[^ \t\n,;/]", templine)
            tempidx = tb_line.index(word.group())
            if isinput == 1:
                tb_line = tb_line[0:tempidx]+ "bit " + tb_line[tempidx:]
            else:
                tb_line = tb_line[0:tempidx]+ "logic " + tb_line[tempidx:]



        ########################################################################
        #construct TB SIGNAL DECLARATIONS
        ########################################################################

        # if the line ends with a , change to ; #
        # first we must rid ourselves of end of line comments #

        isstar = 0
        isdouble = 0
#MARK
    #could use both comment types on the same line, this could lead to incorrectly replacing "//" with "/*"
        if re.search(r"/\*", tb_line):
            isstar = 1
        if re.search(r"//", tb_line):
            isdouble = 1
        broken_line = comments_re.split(tb_line,1)
        reverse_string = broken_line[0][::-1]

        if comma_re.match(reverse_string):
            if isrst == 1:
                reverse_string = comma_replace_re.sub(r";1 = ", reverse_string, 1)
            elif isinput == 2:
                reverse_string = comma_replace_re.sub(r";)(", reverse_string, 1)
            else:
                reverse_string = comma_replace_re.sub(r";", reverse_string, 1)

        broken_line[0] = reverse_string[::-1]

        # put the broken up line back together #
        if len(broken_line) > 1:
            if isdouble == 1:
                tb_line = "//".join(broken_line)
            if isstar == 1:
                tb_line = "/*".join(broken_line)
        else:
            tb_line = broken_line[0]
        
        if isinput <> 2:
            tb_signals.append(tb_line)


        ########################################################################
        #construct various SIGNALS
        ########################################################################

        # Get rid of 'logic', 'wire', #
        if logic_re.match(dut_line):
            dut_line = logic_re.sub("", dut_line, 1)
        if wire_re.match(dut_line):
            dut_line = wire_re.sub("", dut_line, 1)

        # Get rid of everything in []. #
        dut_line = bracket_contents_re.sub("", dut_line) 

        # Since everything in brakets is gone, if there are two words then a comma,  #
        # we can get rid of that first word.  Which should be a struct or something. #

        if structure_re.match(dut_line):
            dut_line = structure_replace_re.sub("", dut_line, 1)

#MARK
    #will need to be changed:   (will delete all of spaces in end of line comments!)
        dut_line = re.sub(r"[ \t]", "", dut_line)
        signal = re.search(r"^[^ \n;,\t]*", dut_line)
        temp = re.sub(r"^[^ \n;,\t]*", "" , dut_line, 1)
        dut_line = "." + signal.group() + "(" + signal.group() + ")" + temp
        temp = re.sub(r"/[/*].*", "" , temp)
        ref_line = "." + signal.group() + "(" + signal.group() + "_ref)" + temp
        mon_in_line = "." + signal.group() + "_ref(" + signal.group() + "_ref)" + temp
        if isclk == 1:
            clk_signals.append(signal.group())
        elif iscimringin == 1:
            cim_in_signal.append(signal.group())
        elif iscimringout == 1:
            cim_out_signal.append(signal.group())
        elif isrst == 1:
            rst_signals.append(signal.group())



        isduplicate = 0
        dut_signals.append(dut_line)
        if isinput == 1:    # input signals #
            # add signal to reference model #
            ref_in_signals.append(dut_line)
            if iscimringin <> 1 and iscimringout <> 1:
                bus_in_signals.append(dut_line)
        elif isinput == 2:  # interface signals #
            # make sure interface is declared without the 'interface_name.modport_name' #
            if re.search(r"^[ \t]*[^ \n,;/\t.]+\.[^ \n,;/\t.]+", tb_line):
                line_for_tb = re.sub(r"\.[^ \n,;/\t.]+", "", tb_line, 1)
            tb_signals.append(line_for_tb)
            line_for_tb = re.sub(r"[ \t]*[^ \n,;/\t.()]+[ \t]+([^ \n,;/\t.()]+)", add_ref_to_group1, line_for_tb, 1)
            tb_signals.append(line_for_tb)
            isduplicate = 1

            line_for_ref = re.sub(r"[ \t]*\.[^ \n,;/\t]+[ \t]*\(([^ \n,;/\t]+)\).*", add_ref_to_group1_twice, dut_line, 1)
            if not re.search(r"[^/,]*,", line_for_ref):
                line_for_ref = re.sub(r"\)", "),", line_for_ref, 1)
            ref_in_signals.append(line_for_ref)
            ref_in_signals.append(dut_line)
            bus_in_signals.append(dut_line)
            mon_in_signals.append(line_for_ref)
            mon_in_signals.append(dut_line)
        else:   # output signals #

            if not comma_replace_re.search(mon_line):   # comma doesn't exist #
                mon_line = re.sub(r"([^ \n,;/\t]+)[ \t]+([^ \n,;/\t]+)[ \t]+([^ \n,;/\t]+)", add_ref_comma, mon_line, 1)
                holdline = mon_signals[-1]
                mon_signals[-1] = mon_line
                mon_signals.append(holdline)
            else:                                       # comma exists #
                mon_line = re.sub(r"([^ \n,;/\t]+)[ \t]*,", add_ref_to_group1, mon_line, 1)
                mon_signals.append(mon_line)
            if not comma_replace_re.search(mon_in_line):
                mon_in_line = re.sub(r"\)", "),", mon_in_line,1)
                holdline = mon_in_signals[-1]
                mon_in_signals[-1] = mon_in_line
                mon_in_signals.append(holdline)
            else:
                mon_in_signals.append(mon_in_line)
            isduplicate = 1

            # make sure what you're replacing is the signal #
            if re.search(";", tb_line):   # semicolon exists #
                line_for_tb = re.sub(r"([^ \n,;/\t]+)[ \t]*;", add_ref_to_group1, tb_line, 1)
            else:
                broken_line = comments_re.split(tb_line,1)
                if len(broken_line) > 1:
                    line_for_tb = re.sub(r"([^ \n,;/\t]+)[ \t\n]*$", add_ref_to_group1, broken_line[0], 1) + broken_line[1:]
                else:
                    line_for_tb = re.sub(r"([^ \n,;/\t]+)[ \t\n]*$", add_ref_to_group1, broken_line[0], 1)

            tb_signals.append(line_for_tb)
            assert_signals.append(signal.group())
            assert_signals.append(signal.group()+"_ref")
            mon_in_signals.append(dut_line)
            ref_in_signals.append(ref_line)
    else:
        ref_signals.append(line)
        dut_signals.append(line)
        tb_signals.append(line)
f.close()


# for the tb signal declarations, the last signal must have a ; as well (no comma to replace!) #
# first we must, find the last signal, then rid ourselves of end of line comments #

tb_idx = 0
# run past empty lines in tb_signals #
for line in tb_signals[::-1]:
    tb_idx -= 1
    if re.match("^[ \t]*\n", line):
        continue
    else:
        break
 
for i in xrange(2):
    broken_line = comments_re.split(tb_signals[tb_idx],1)
    for i in range(len(broken_line[0])-1, -1, -1):
        if broken_line[0][i] == ' ' or broken_line[0][i] == '\n':
            continue
        else:
            if isinput <> 2:
                broken_line[0] = broken_line[0][0:i+1] + ";" + broken_line[0][i+1:]
            else:
                broken_line[0] = broken_line[0][0:i+1] + "();" + broken_line[0][i+1:]
            break
    if len(broken_line) > 1:
        tb_signals[tb_idx] = broken_line[0] + broken_line[1]
    else:
        tb_signals[tb_idx] = broken_line[0]
    # if a duplicate signal was created for the reference model, we'll need to add a ; to that as well #
    if isduplicate == 1:
        tb_idx -= 1
    else:
        break

#MARK
#   this is cheating... and may not work.
#need to rid ourselves of some commas
mon_signals[-1] = comma_replace_re.sub("", mon_signals[-1], 1)
mon_in_signals[-1] = comma_replace_re.sub("", mon_in_signals[-1], 1)
bus_signals[-1] = comma_replace_re.sub("", bus_signals[-1], 1)
 













#-------------------------------------------------------------------------------
#                               Create TESTBENCH
#-------------------------------------------------------------------------------


output = ""
markers = ["HEADER", "DECLARATION", "OPTIONS", "CLOCKS", "RESETS", "INSTANTIATE PARTS", "CLOSE", "PARITY TASK"]
tb_file_name = tb_path_name + module_name + '_mytb.sv'
f_exists, starts, ends, lines = GetFileMarkers(markers, tb_file_name)
SwitchMarkerDomain(-1, 0)




output += "`timescale 1ps / 1ps\n"
output += "\n"
output += "\n"
output += "\n"

#MARK
 #unfinished
output += "// the following are examples of plusargs to override default behavior\n"
output += "// ./<compile> +DUMP                                 -set to get the wavedump\n"
output += "// ./<compile> +NODUMP                               -set to skip the wavedump (takes precidence over DUMP)\n"
output += "\n"
output += "// ./simv +seed=1                                    -set randomize seed values\n"
output += "// ./simv +runtime=500000                            -set the amount of time for the test to run\n"
output += "// ./simv +<clock signal (lowercase)>period=400      -set the clock period\n"
output += "// Example:          ./simv +sysclkperiod=800      \n"
output += "// ./simv +<reset signal (lowercase)>time=400        -set the amount of time the reset signal is asserted at the beginning\n"
output += "// Example:          ./simv +resetasynctime=50     \n"
output += "// \n"




SwitchMarkerDomain(0, 1)




output += "module tb();\n"
output += "\n"

# test bench signals declarations #
for line in tb_signals:
    output += line




SwitchMarkerDomain(1, 2)




################################################################################
#Testbench                  WAVEDUMP & RANDOM SEED & LOG FILE
################################################################################

output += "initial begin\n"
output += "\t`ifndef NODUMP\n"
output += "\t\t`ifndef DUMP\n"
output += "\t\t`else\n"
output += "\t\t\t$vcdpluson;\n"
output += "\t\t\t$vcdplusmemon;\n"
output += "\t\t`endif\n"
output += "\t`endif\n"
output += "end\n"

output += "\n"
output += "\n"
output += "\n"

output += "int seed = 2;\n"
output += "int dummy;\n"
output += "int f_log;\n"
output += "string log_name;\n"
output += "string seed_str;\n"
output += "\n"
output += "initial begin\n"
output += "\tif ( !$value$plusargs (\"seed=%0d\", seed) ) begin\n"         # (if there is no value specified...) #
output += "\t\tseed_str.itoa(seed);\n"
output += "\t\tlog_name = {\"log/run.log_\", seed_str};\n"
output += "\t\tf_log = $fopen(log_name, \"w\");\n"
output += "\t\t$fdisplay(f_log, \"\No seed specified, %d\", seed);\n"
output += "\tend\n"
output += "\telse begin\n"
output += "\t\tseed_str.itoa(seed);\n"
output += "\t\tlog_name = {\"log/run.log_\", seed_str};\n"
output += "\t\tf_log = $fopen(log_name, \"w\");\n"
output += "\t\t$fdisplay(f_log, \"\Given seed, %d\", seed);\n"
output += "\t\tdummy = $urandom(seed);\n"
output += "\t\tdummy = $random(seed);\n"
output += "\t\t$srandom(seed);\n"
output += "\tend\n"
output += "end\n"




SwitchMarkerDomain(2, 3)




################################################################################
#Testbench                  CLOCK GENERATORS
#    remember clk_signals only has the clock signal name
################################################################################

for sig in clk_signals:
    temparr = ClksToSkip(sig)           # [skip, txt_number, issys] #
    if temparr[0] == 1:
        continue
    output += "int " + sig + "period;\n"
output += "\n"

mysysclk_idx = -1
counter = -1
for sig in clk_signals:
    counter += 1
    txt_number = "UNKNOWN"
    temparr = ClksToSkip(sig)           # [skip, txt_number, issys] #
    if temparr[0] == 1:
        output += "initial begin\n"
        output += "\t" + sig + " = 0;\n"
        output += "end\n"
        output += "\n"
        continue
    if temparr[1] <> '0':
        txt_number = temparr[1]
    if temparr[2] == 1:
        mysysclk_idx = counter
    
    output += "initial begin\n"
    output += "\tif ( !$value$plusargs (\"" + sig.lower() + "period=%0d\", " + sig + "period) ) \n"         # (if there is no value specified...) #
    output += "\t\tforever #" + txt_number + " " + sig + " = !" + sig + ";\n"
    output += "\telse\n"
    output += "\t\tforever #(" + sig + "period/2) " + sig + " = !" + sig + ";\n"
    output += "end\n"
    output += "\n"

if mysysclk_idx == -1:
    print "ERROR: no sys clock found, incorrect extrapolations will be made."




SwitchMarkerDomain(3, 4)




################################################################################
#                       Testbench RESETS
################################################################################

for sig in rst_signals:
    output += "int " + sig + "time;\n"
output += "\n"
default_rst_number = '20'
bm_rst_idx = -1
count = -1
for sig in rst_signals:
    count += 1
    if re.search("Async", sig, re.I) or re.search("Sys", sig, re.I):
        bm_rst_idx = count
    output += "initial begin\n"
    output += "\tif ( !$value$plusargs (\"" + sig.lower() + "time=%0d\", " + sig + "time) ) begin\n"
    output += "\t\trepeat ( " + default_rst_number + " )  @ (posedge " + clk_signals[mysysclk_idx] + ");\n"
    output += "\t\t" + sig + " = 0;\n"
    output += "\tend\n"
    output += "\telse begin\n"
    output += "\t\trepeat ( " + sig + "time )  @ (posedge " + clk_signals[mysysclk_idx] + ");\n"
    output += "\t\t" + sig + " = 0;\n"
    output += "\tend\n"
    output += "end\n"
    output += "\n"




SwitchMarkerDomain(4, 5)
        



################################################################################
#                       INSTANTIATE MODULES
################################################################################

#MARK
    #this is bm instantiation is GSBU, XPP specific
#Instantiate BM module
if len(cim_out_signal) > 0 and len(cim_in_signal) > 0:
    output += "bm mybm (\n"
    output += "." + clk_signals[mysysclk_idx] + "(" + clk_signals[mysysclk_idx] + "),\n"
    output += ".reset(" + rst_signals[bm_rst_idx] + "),\n"
    output += ".cimRingIn(" + cim_out_signal[0] + "),\n"
    output += ".cimRingOut(" + cim_in_signal[0] + ")\n"
    output += ");"

output += "\n"
output += "\n"
output += "\n"

#Instantiating DUT module
output += module_name+" DUT (\n"
for sig in dut_signals:
    output += sig
output += ");\n"

output += "\n"
output += "\n"
output += "\n"

#Instantiate REFERENCE module
output += "reference_model " + reference_model_name + " (\n"
for sig in ref_in_signals:
    output += sig
output += ");\n"

output += "\n"
output += "\n"
output += "\n"

#Instantiate MONITOR
output += "monitor " + monitor_name + " (\n"
for sig in mon_in_signals:
    output += sig
output += ");\n"

output += "\n"
output += "\n"
output += "\n"

#Instantiate BUS MODEL
output += "bus_model " + bus_model_name + " (\n"
for sig in bus_in_signals:
    output += sig
output += ");\n"




SwitchMarkerDomain(5, 6)




output += "int runtime;\n"
output += "initial begin\n"
output += "\tif ( $value$plusargs (\"runtime=%0d\", runtime) )\n"
output += "\t\t#(runtime) $finish;\n"
output += "\telse\n"
output += "\t\t#20000 $finish;\n"
output += "end\n"

#MARK
    #never instantiated the test!?
    #still works though...

output += "\n"
output += "\n"
output += "\n"

output += "endmodule\n"




SwitchMarkerDomain(6, 7)




#######################################################################
#               Create PARITY FAULT INJECTION TASK
#######################################################################



try:
    f = open(options.parity_file,'r')
    parity_lines = f.readlines()
    f_exists = 1
    f.close()
except IOError:
    f_exists = 0
if f_exists == 1:
    for line in parity_lines:
        parse_mobj = re.match(r"[ \t]*([a-zA-Z0-9_]+)[ \t]+([a-zA-Z0-9_]+)[ \t]+([a-zA-Z0-9.$_]+)", line)
        name = parse_mobj.group(1)
        index = parse_mobj.group(2)
        path = parse_mobj.group(3)
        #output += "\ttask automatic InjectParErr(\n"
        output += "task InjectParFault_" + name + index + "(\n"
        output += "\tinput int length,\n"
        output += "\toutput int bitFlipped\n"
        output += "\t);\n"
        output += "\n"
        #output += "\t//output [<address width>-1:0] addr;\n"
        #output += "\t//output [<data width>-1:0]    data;\n"
        output += "\t\tint counter;\n"
        output += "\t\tbit forceOn;\n"
        output += "\t\tbit temp;\n"
        output += "\n"
        output += "\t\trepeat (2) @(posedge tb." + clk_signals[mysysclk_idx] + ");\n"
        output += "\n"
        output += "\t\tif ( length <= 16 ) begin\n"
        output += "\t\t\tcounter = 0;\n"
        output += "\t\tend\n"
        output += "\t\telse begin\n"
        output += "\t\t\tcounter = $random % (length / 16);\n"
        output += "\t\tend\n"
        output += "\n"

        #MARK (temperary)
        #output += "\t\tbitFlipped = $random % <data width + parity width>;\n"
        output += "\t\tbitFlipped = $random % 1;\n"

        output += "\n"
        output += "\t\tif ( counter == 0 )\n"
        output += "\t\t\t@(negedge tb." + clk_signals[mysysclk_idx] + ");\n"
        output += "\n"
        output += "\t\twhile ( |counter ) begin\n"
        output += "\t\t\t@(negedge tb." + clk_signals[mysysclk_idx] + ");\n"
        output += "\t\t\tcounter--;\n"
        output += "\t\tend\n"
        output += "\n"
        output += "\t\t// The data path is different for each port\n"
        output += "\t\ttemp = " + path + ";\n"
        output += "\n"
        output += "\t\tforce " + path + " = !temp;\n"
        output += "\n"
        output += "\t\t$fdisplay (tb.f_log, \"DBG TST @%0t: %m, Injecting Parity Error, bit=%0d\", $time, bitFlipped);\n"
        output += "\n"
        output += "\t\t@(negedge tb." + clk_signals[mysysclk_idx] + ");\n"
        output += "\n"
        output += "\t\trelease " + path + ";\n"
        output += "\n"
        output += "\tendtask\n"
        output += "\n"
        output += "\n"



SwitchMarkerDomain(7, -1)


f = open(tb_file_name,'w')
f.write(output)
f.close()












#-------------------------------------------------------------------------------
#                                   REFERENCE MODEL
#-------------------------------------------------------------------------------


output = ""
markers = ["DECLARATION", "CLOSE"]
reference_model_file_name = reference_model_path_name + module_name + '_myreference_model.sv'
f_exists, starts, ends, lines = GetFileMarkers(markers, reference_model_file_name)
SwitchMarkerDomain(-1, 0)


output += "`timescale 1ps / 1ps\n"
output += "\n"
output += "module reference_model(\n"

# signal declarations #
for line in ref_signals:
    output += line



SwitchMarkerDomain(0, 1)



output += "endmodule\n"



SwitchMarkerDomain(1, -1)



f = open(reference_model_file_name,'w')
f.write(output)
f.close()













#-------------------------------------------------------------------------------
#                               Create MONITOR
#-------------------------------------------------------------------------------



output = ""
markers = ["DECLARATION", "CLOSE"]
monitor_file_name = monitor_path_name + module_name + '_mymonitor.sv'
f_exists, starts, ends, lines = GetFileMarkers(markers, monitor_file_name)
SwitchMarkerDomain(-1, 0)



output += "`timescale 1ps / 1ps\n"
output += "\n"
output += "module monitor(\n"

if mysysclk_idx > -1:
    output += "input logic " + clk_signals[mysysclk_idx] + ",\n"

for line in mon_signals:
    output += line
output += ");\n"



SwitchMarkerDomain(0, 1)



#output += "always @(posedge " + clk_signals[mysysclk_idx] + ") begin\n"
#for x in range(0, len(assert_signals), 2):
#    sig = re.sub(r"^\n[ \t]*,", "", assert_signals[x][::-1], 1)
#    sig2 = re.sub(r"^\n[ \t]*,", "", assert_signals[x+1][::-1], 1)
#    output += "\ta" + str(x) + ": assert (" + sig[::-1] + " == " + sig2[::-1] + ")\n"
#    output += "\telse $error(\"ERROR: " + assert_signals[x] + " reference signal does not match DUT signal\");\n"
#output += "end\n"





output += "endmodule\n"



SwitchMarkerDomain(1, -1)

f = open(monitor_file_name,'w')
f.write(output)
f.close()












#-------------------------------------------------------------------------------
#                               Create BUS MODEL
#-------------------------------------------------------------------------------


output = ""
markers = ["DECLARATION", "PARITY", "CLOSE"]
bus_model_file_name = bus_model_path_name + module_name + '_mybus.sv'
f_exists, starts, ends, lines = GetFileMarkers(markers, bus_model_file_name)
SwitchMarkerDomain(-1, 0)



output += "`timescale 1ps / 1ps\n"
output += "\n"
output += "module bus_model(\n"

# to have the system clock be an input: #
#if mysysclk_idx > -1:
#    output += "input logic " + clk_signals[mysysclk_idx] + ",\n"

for line in bus_signals:
    output += line
output += ");\n"



SwitchMarkerDomain(0, 1)



################################################################################
#                           drive PARITY SIGNALS
################################################################################

output += "int isparityerror;\n"
output += "int j;\n"
output += "int par_sig_size;\n"
output += "int toflip;\n"
output += "\n"

firsttime = 1
for sig_pair in parity_signals:
    # search to see if the parity signal is an output to be driven, if so, drive it #
    for entry in modport_outputs:
        if sig_pair[0] == entry[0]:
            if firsttime == 1:
                output += "always @(*) begin\n"
                if is_parity_errors <> 1:
                    output += "\tisparityerror = 0;\n"
                else:
                    output += "\tisparityerror = $urandom % " + par_err_chance_string + ";\n"
                firsttime = 0
            output += "\tpar_sig_size = $size(" + sig_pair[2] + "." + sig_pair[0] + ");\n"
            output += "\tfor(j=0; j < par_sig_size; j++)\n"
            output += "\t\t" + sig_pair[2] + "." + sig_pair[0] + "[j] = (^(" + sig_pair[2] + "." + sig_pair[1] + "[j+:64]));\n"
            output += "\tif (isparityerror == 1) begin\n"
            output += "\t\ttoflip = $urandom % par_sig_size;\n"
            output += "\t\t" + sig_pair[2] + "." + sig_pair[0] + "[toflip] = ~(" + sig_pair[2] + "." + sig_pair[0] + "[toflip]);\n"
            output += "\tend\n"
#TEMP
            #output += "$display(\"\");\n"
            #output += "$display(\"%h\", dpmRing_if.dpmDataRingIn);\n"
            #output += "$display(\"%h\", dpmRing_if.dpmDataParityRingIn);\n"

            output += "\n"
            break
output += "end\n"



SwitchMarkerDomain(1, 2)



output += "endmodule\n"



SwitchMarkerDomain(2, -1)



f = open(bus_model_file_name,'w')
f.write(output)
f.close()












#-------------------------------------------------------------------------------
#                               Create PROGRAM
#-------------------------------------------------------------------------------



output = ""
markers = ["DECLARATION", "CLOSE"]
test_file_name = test_path_name + module_name + '_mytest.sv'
f_exists, starts, ends, lines = GetFileMarkers(markers, test_file_name)
SwitchMarkerDomain(-1, 0)



output += "`timescale 1ps / 1ps\n"
output += "\n"
output += "\n"
output += "\n"
output += "program test();\n"



SwitchMarkerDomain(0, 1)



output += "endprogram\n"



SwitchMarkerDomain(1, -1)



f = open(test_file_name,'w')
f.write(output)
f.close()




print "Done with: " + module_name + "\n\n"

