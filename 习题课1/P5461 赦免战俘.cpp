#include <iostream>
#include <vector>
using namespace std;
void func(vector<vector<int>> &arr, int pos_x, int pos_y, int size){
    if(size == 1) return;

    for(int i = pos_x; i < pos_x + size / 2; ++i){
        for(int j = pos_y; j < pos_y + size / 2; ++j){
            arr[i][j] = 0;
        }
    }
    func(arr, pos_x, pos_y + size / 2, size / 2);
    func(arr, pos_x + size / 2, pos_y, size / 2);
    func(arr, pos_x + size / 2, pos_y + size / 2, size / 2);
}

int main(){
    int n;
    cin >> n;
    int size = 1 << n;
    vector<vector<int>> arr(size, vector<int>(size, 1));
    func(arr, 0, 0, size);
    for(int i = 0; i < size; ++i){
        for(int j = 0; j < size; ++j){
            cout << arr[i][j] << ' ';
        }
        cout << endl;
    }

}