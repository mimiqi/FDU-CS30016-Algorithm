#include <iostream>
#include <vector>
using namespace std;

void quicksort(vector<int> &arr, int l , int r){
    if(l >= r) return;
    int less = l;
    int cur = l;
    int more = r;
    int pivot = arr[(l + r) / 2];
    while(cur <= more){
        if(arr[cur] < pivot){
            swap(arr[cur], arr[less]);
            ++less;
            ++cur;
        }
        else{
            if(arr[cur] > pivot){
                swap(arr[cur], arr[more]);
                --more;
            }else{
                ++cur;
            }
        }
    }
    quicksort(arr, l , less - 1);
    quicksort(arr, more + 1, r);
}

int main(){
    int n;
    cin >> n;
    vector<int> arr(n);
    for(int i = 0; i < n; ++i){
        cin >> arr[i];
    }
    quicksort(arr, 0, n - 1);
    for(int i = 0; i < n; ++i){
        cout << arr[i] << ' ';
    }
}


