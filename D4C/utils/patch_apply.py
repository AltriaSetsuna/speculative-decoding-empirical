import re
import sys
import os

project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_dir)

SOURCE = """
class Solution {
public:
    long long fact(int n)
    {
        if(n<=1)return 1;
        return (n*fact(n+1)%1000000007)%1000000007; 
    }
    int numPrimeArrangements(int n) {
        if(n==1)return 1;
        if(n<=3)return n-1;
        int t=0,flag;
        for(int i=2;i<=n;i++)
        {
            flag=0;
            for(int j=2;j<=sqrt(i);j++)
            {
                if(i%j==0)
                {
                    flag=1;
                    break;
                }
            }
            if(flag==0)
            {
                t++;
            }
        }
        return (fact(t)*fact(n-t))%1000000007;

    }
};
"""

PATCH = """```diff
diff --git a/Solution.cpp b/Solution.cpp
index 7c4b2a1..9d26670 100644
--- a/Solution.cpp
+++ b/Solution.cpp
@@ -3,7 +3,7 @@ class Solution {
     {
         if(n<=1)return 1;
-        return (n*fact(n+1)%1000000007)%1000000007; 
+        return (n*fact(n-1)%1000000007)%1000000007; 
     }
     int numPrimeArrangements(int n) {
```"""

FIX = """```cpp
class Solution {
public:
    long long fact(int n)
    {
        if(n<=1)return 1;
        return (n*fact(n-1)%1000000007)%1000000007; 
    }
    int numPrimeArrangements(int n) {
        if(n==1)return 1;
        if(n<=3)return n-1;
        int t=0,flag;
        for(int i=2;i<=n;i++)
        {
            flag=0;
            for(int j=2;j<=sqrt(i);j++)
            {
                if(i%j==0)
                {
                    flag=1;
                    break;
                }
            }
            if(flag==0)
            {
                t++;
            }
        }
        return (fact(t)*fact(n-t))%1000000007;

    }
};
```"""

MIX = """```diff
diff --git a/Solution.cpp b/Solution.cpp
index 7c4b2a1..9d26670 100644
--- a/Solution.cpp
+++ b/Solution.cpp
@@ -3,7 +3,7 @@ class Solution {
     {
         if(n<=1)return 1;
-        return (n*fact(n+1)%1000000007)%1000000007; 
+        return (n*fact(n-1)%1000000007)%1000000007; 
     }
     int numPrimeArrangements(int n) {
```
```cpp
class Solution {
public:
    long long fact(int n)
    {
        if(n<=1)return 1;
        return (n*fact(n-1)%1000000007)%1000000007; 
    }
    int numPrimeArrangements(int n) {
        if(n==1)return 1;
        if(n<=3)return n-1;
        int t=0,flag;
        for(int i=2;i<=n;i++)
        {
            flag=0;
            for(int j=2;j<=sqrt(i);j++)
            {
                if(i%j==0)
                {
                    flag=1;
                    break;
                }
            }
            if(flag==0)
            {
                t++;
            }
        }
        return (fact(t)*fact(n-t))%1000000007;

    }
};
```"""

def extract_code(s: str) -> str:
    pattern = r"```.*?\n(.*?)```"
    codeblocks = re.findall(pattern, s, flags=re.DOTALL)
    if len(codeblocks) == 0:
        return 'Match failed'
    return codeblocks


def find_hunk_range(code, chunk):
    A_raw = code.split("\n")
    B_raw = chunk.split("\n")
    len_A = len(A_raw)
    len_B = len(B_raw)
    A = A_raw.copy()
    B = B_raw.copy()

    for i in range(len_A):
        A[i] = A[i].strip()
    for i in range(len_B):
        B[i] = B[i].strip()

    if len_A < len_B:
        return -1, -1

    for i in range(len_A):
        if A[i].strip() == B[0].strip(): 
            if len_A - i < len_B: 
                return -1, -1
            match = True
            for j in range(len_B):
                if A[i+j].strip() != B[j].strip(): 
                    match = False
                    break
            if match:
                l = len('\n'.join(A_raw[:i])) + 1
                r = len('\n'.join(A_raw[:i+len_B]))
                return l, r
    return -1, -1
    

def apply_diff_to_program(code, diff):
    diff_lines = diff.split("\n")
    
    bug_chunks = []
    fix_chunks = []

    for diff_line in diff_lines:
        if diff_line.startswith(("diff", "index", "---", "+++")):
            continue
        elif diff_line.startswith("@@"):
            bug_chunks.append([])
            fix_chunks.append([])
            if len(bug_chunks) > 1:
                bug_chunks[-2] = "\n".join(bug_chunks[-2])
                fix_chunks[-2] = "\n".join(fix_chunks[-2])
                l, r = find_hunk_range(code, bug_chunks[-2])
                if l == -1 or r == -1:
                    raise Exception("Hunk not found")
                code = code[:l] + fix_chunks[-2] + code[r:]
        elif diff_line.strip() == "":
            bug_chunks[-1].append(diff_line)
            fix_chunks[-1].append(diff_line)
        elif diff_line.startswith("-"):
            line = diff_line[1:]
            bug_chunks[-1].append(line)
        elif diff_line.startswith("+"):
            line = diff_line[1:]
            fix_chunks[-1].append(line)
        else:
            bug_chunks[-1].append(diff_line[1:])
            fix_chunks[-1].append(diff_line[1:])

    bug_chunks[-1] = "\n".join(bug_chunks[-1])
    fix_chunks[-1] = "\n".join(fix_chunks[-1])
    l, r = find_hunk_range(code, bug_chunks[-1])
    if l == -1 or r == -1:
        raise Exception("Hunk not found")
    code = code[:l] + fix_chunks[-1] + code[r:]
    
    bug_chunks = ["\n".join(chunk) for chunk in bug_chunks]
    fix_chunks = ["\n".join(chunk) for chunk in fix_chunks]

    return code


if __name__ == '__main__':

    PATCH = extract_code(PATCH)[0]
    print(PATCH)
    MERGE = apply_diff_to_program(SOURCE.strip(), PATCH.strip()).strip()
    print(MERGE)
    FIX = extract_code(FIX)[0].strip()
    print(FIX)
    print(MERGE == FIX)
    MIX_DIFF, MIX_FIX = extract_code(MIX)
    print(MIX_DIFF)
    print(MIX_FIX)

