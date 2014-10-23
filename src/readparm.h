// readparm.h
#ifndef READPARM_H
#define READPARM_H

#include <locale>
#include <string>
#include <map>
#include <vector>

#define MAX_HOLLERITH_SIZE 8

// Return codes
enum ExitStatus {OK=0, NOOPEN=1, EMPTY=2, NOVERSION=3, ERR=4};

// Some string routines
inline std::string strip(const std::string &input) {
    size_t first_char = input.size();
    size_t last_char = first_char;
    for (size_t i = 0; i < input.size(); i++) {
        char ci = input[i];
        if (ci == ' ' || ci == '\t' || ci == '\n' || ci == '\r') continue;
        first_char = i;
        break;
    }
    for (size_t i = input.size() - 1; i >= first_char; i--) {
        char ci = input[i];
        if (ci == ' ' || ci == '\t' || ci == '\n' || ci == '\r') continue;
        last_char = i;
        break;
    }
    return input.substr(first_char, last_char-first_char+1);
}

inline std::string rstrip(const std::string &input) {
    size_t last_char = input.size();
    for (size_t i = input.size() - 1; i >= 0; i--) {
        char ci = input[i];
        if (ci == ' ' || ci == '\t' || ci == '\n' || ci == '\r') continue;
        last_char = i;
        break;
    }
    return input.substr(0, last_char+1);
}

inline std::string upper(const std::string &input) {
    std::locale loc;
    std::string retval = input;
    for (size_t i = 0; i < input.size(); i++) {
        retval[i] = std::toupper(retval[i], loc);
    }
    return retval;
}

inline std::string lower(const std::string &input) {
    std::locale loc;
    std::string retval = input;
    for (size_t i = 0; i < input.size(); i++) {
        retval[i] = std::tolower(retval[i], loc);
    }
    return retval;
}

/* Handle relatively simple Fortran formats, and fall back to Python parsing if
 * the format is unrecognized.
 */
enum ParmDataType {UNKNOWN=0, INTEGER, FLOAT, HOLLERITH};
ParmDataType parseFormat(const std::string &fmt, int &ncols, int &width);

/* Data types for topology file data. Use a union to store all parm data we know
 * how to parse (either a 4-character string, integer, or floating point number)
 * and define some types to store the prmtop data we parse.
 */
union ParmData {
    char c[MAX_HOLLERITH_SIZE]; // don't forget the null character
    int i;
    double f;
};

typedef struct {
    ParmDataType dataType;
    std::string fmt;
} ParmFormatType;

typedef std::vector<ParmData> ParmDataVec;
typedef std::map<std::string, ParmDataVec> ParmDataMap;
typedef std::map<std::string, std::vector<std::string> > ParmStringMap;
typedef std::map<std::string, ParmFormatType> ParmFormatMap;

/* Parses the Amber topology file and stores the data inside the hash maps
 * passed to the function. Returns 0 if parsing was successful and 1 otherwise
 */
ExitStatus readparm(const std::string &fname, std::vector<std::string> &flagList,
                    ParmDataMap &parmData, ParmStringMap &parmComments,
                    ParmStringMap &unkParmData, ParmFormatMap &parmFormats,
                    std::string &version);

#endif /* READPARM_H */
