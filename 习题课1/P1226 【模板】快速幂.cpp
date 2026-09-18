#include <iostream>

using namespace std;

int main(){
    long long init_a;
    long long init_b;
    long long init_p;

    cin >> init_a >> init_b >> init_p;

    long long result = 1;
    long long b = init_b;


    long long base = init_a % init_p;
    while(b > 0){
        if(b % 2 == 1){
            result = result * base % init_p;
        }
        base = base * base % init_p;
        b = b >> 1;
    }

    cout << init_a << "^" << init_b << " mod " << init_p << "=" << result << endl;


}