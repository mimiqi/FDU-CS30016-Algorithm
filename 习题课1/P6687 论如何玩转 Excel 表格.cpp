#include <iostream>
#include <vector>
#include <cstdlib>
using namespace std;
long long mergeCount(vector<int> &arr, vector<int> &tmp, int left, int right){
    if(left >= right) return 0;

    int mid = (right - left) / 2 + left;
    long long answer = 0;
    answer = answer + mergeCount(arr, tmp, left, mid);
    answer = answer + mergeCount(arr, tmp, mid + 1, right);
    int i = left;
    int j = mid + 1;
    int k = left;
    while(i <= mid && j <= right){
        if(arr[i] <= arr[j]){
            tmp[k] = arr[i];
            ++i;
            ++k;
        }
        else{
            answer += mid - i + 1;
            tmp[k] = arr[j];
            ++j;
            ++k;
        }
    }
    while(i <= mid){
        tmp[k] = arr[i];
        ++i;
        ++k;
    }   
    while(j <= right){
        tmp[k] = arr[j];
        ++j;
        ++k;        
    }
    for(int p = left; p <= right; ++p){
        arr[p] = tmp[p];
    }
    return answer;
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    cin >> n;
    vector<int> curTop(n);
    vector<int> curBot(n);
    vector<int> tarTop(n);
    vector<int> tarBot(n);

    for(int i = 0; i < n; ++i){
        cin >> curTop[i];
    }
    for(int i = 0; i < n; ++i){
        cin >> curBot[i];
    }
    for(int i = 0; i < n; ++i){
        cin >> tarTop[i];
    }
    for(int i = 0; i < n; ++i){
        cin >> tarBot[i];
    }
    vector<int> tarCol(2 * n + 1);
    for(int col = 0; col < n; ++col){
        tarCol[tarTop[col]] = col;
        tarCol[tarBot[col]] = col;
    }
    vector<int> permutation(n);
    for(int curCol = 0; curCol < n; ++curCol){
        int upper = curTop[curCol];
        int lower = curBot[curCol];
        int targetColOfUpper = tarCol[upper];
        int targetColOfLower = tarCol[lower];

        if(targetColOfUpper != targetColOfLower){
            cout << "dldsgay!!1\n";
            return 0;
        }

        int targetCol = targetColOfUpper;
        permutation[curCol] = targetCol;

        bool reserved = !(curTop[curCol] == tarTop[targetCol] && curBot[curCol] == tarBot[targetCol]);
        int moveParity = abs(curCol - targetCol) % 2;
        if(moveParity != static_cast<int>(reserved)){
            cout << "dldsgay!!1\n";
            return 0;            
        }
    }

    vector<int> tmp(n);
    long long ans = 0;
    if(n > 0){
        ans = mergeCount(permutation, tmp, 0, n - 1);
    }
    cout << ans << '\n';
    return 0;
}