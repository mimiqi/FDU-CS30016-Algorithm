#include <iostream>
#include <vector>

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
    int size;
    cin >> size;
    vector<int> arr(size);
    vector<int> temp(size);
    for(int i = 0; i < size; i++){
        cin >> arr[i];
    }
    long long result = mergeCount(arr, temp, 0, size - 1);
    cout << result << endl;
}