#include <iostream>
#include <vector>
using namespace std;
void func(vector<vector<int>> &arr, int &cur, int top_left_x, int top_left_y, int size, int spec_left_x, int spec_left_y){
    if(size == 2){
        for(int i = top_left_x; i < top_left_x + size; ++i){
            for(int j = top_left_y; j < top_left_y + size; ++j){
                if(arr[i][j] == -1) arr[i][j] = cur;
            }
        }
        ++cur;
        return;
    }

    
        if(spec_left_x < top_left_x + size / 2 && spec_left_y < top_left_y + size / 2){//左上

            arr[top_left_x + size / 2 - 1][top_left_y + size / 2] = cur;//右上
            arr[top_left_x + size / 2][top_left_y + size / 2 - 1] = cur;//左下
            arr[top_left_x + size / 2][top_left_y + size / 2] = cur;//右下
            ++cur;
            func(arr, cur, top_left_x, top_left_y, size / 2, spec_left_x, spec_left_y);//左上
            func(arr, cur, top_left_x, top_left_y + size / 2, size / 2, top_left_x + size / 2 - 1, top_left_y + size / 2);//右上
            func(arr, cur, top_left_x + size / 2, top_left_y, size / 2, top_left_x + size / 2, top_left_y + size / 2 - 1);//左下
            func(arr, cur, top_left_x + size / 2, top_left_y + size / 2, size / 2, top_left_x + size / 2, top_left_y + size / 2);//右下
        }
        if(spec_left_x < top_left_x + size / 2 && spec_left_y >= top_left_y + size / 2){//右上
            arr[top_left_x + size / 2 - 1][top_left_y + size / 2 - 1] = cur;//左上

            arr[top_left_x + size / 2][top_left_y + size / 2 - 1] = cur;//左下
            arr[top_left_x + size / 2][top_left_y + size / 2] = cur;//右下
            ++cur;
            func(arr, cur, top_left_x, top_left_y, size / 2, top_left_x + size / 2 - 1, top_left_y + size / 2 - 1);//左上
            func(arr, cur, top_left_x, top_left_y + size / 2, size / 2, spec_left_x, spec_left_y);//右上
            func(arr, cur, top_left_x + size / 2, top_left_y, size / 2, top_left_x + size / 2, top_left_y + size / 2 - 1);//左下
            func(arr, cur, top_left_x + size / 2, top_left_y + size / 2, size / 2, top_left_x + size / 2, top_left_y + size / 2);//右下
        }
        if(spec_left_x >= top_left_x + size / 2 && spec_left_y < top_left_y + size / 2){//左下
            arr[top_left_x + size / 2 - 1][top_left_y + size / 2 - 1] = cur;//左上
            arr[top_left_x + size / 2 - 1][top_left_y + size / 2] = cur;//右上

            arr[top_left_x + size / 2][top_left_y + size / 2] = cur;//右下
            ++cur;
            func(arr, cur, top_left_x, top_left_y, size / 2, top_left_x + size / 2 - 1, top_left_y + size / 2 - 1);//左上
            func(arr, cur, top_left_x, top_left_y + size / 2, size / 2, top_left_x + size / 2 - 1, top_left_y + size / 2);//右上
            func(arr, cur, top_left_x + size / 2, top_left_y, size / 2, spec_left_x, spec_left_y);//左下
            func(arr, cur, top_left_x + size / 2, top_left_y + size / 2, size / 2, top_left_x + size / 2, top_left_y + size / 2);//右下
        }
        if(spec_left_x >= top_left_x + size / 2 && spec_left_y >= top_left_y + size / 2){//右下
            arr[top_left_x + size / 2 - 1][top_left_y + size / 2 - 1] = cur;//左上
            arr[top_left_x + size / 2 - 1][top_left_y + size / 2] = cur;//右上
            arr[top_left_x + size / 2][top_left_y + size / 2 - 1] = cur;//左下

            ++cur;
            func(arr, cur, top_left_x, top_left_y, size / 2, top_left_x + size / 2 - 1, top_left_y + size / 2 - 1);//左上
            func(arr, cur, top_left_x, top_left_y + size / 2, size / 2, top_left_x + size / 2 - 1, top_left_y + size / 2);//右上
            func(arr, cur, top_left_x + size / 2, top_left_y, size / 2, top_left_x + size / 2, top_left_y + size / 2 - 1);//左下
            func(arr, cur, top_left_x + size / 2, top_left_y + size / 2, size / 2, spec_left_x, spec_left_y);//右下
        }

        
    
}


int main(){
    int k;
    cin >> k;
    int x;
    int y;
    cin >> x >> y;
    x--;//修正下标起始
    y--;//修正下标起始
    vector<vector<int>> arr((1 << k), vector<int>((1 << k), -1));
    arr[x][y] = 0;
    int cur = 1;
    func(arr, cur, 0, 0, (1<<k), x, y);
    for(int i = 0; i < (1 << k); ++i){
        for(int j = 0; j < (1 << k); ++j){
            cout << arr[i][j] << ' ';
        }
        cout << endl;
    }
}