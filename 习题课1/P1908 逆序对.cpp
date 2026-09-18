#include <iostream>
#include <vector>

using namespace std;

long long func(vector<int> &arr, vector<int> &temp, int left, int right){

}

int main(){
    int size;
    cin >> size;
    vector<int> arr(size);
    vector<int> temp(size);
    for(int i = 0; i < size; i++){
        cin >> arr[i];
    }
    long long result = func(arr, temp, 0, size - 1);
    cout << result << endl;
}