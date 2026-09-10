#include <stdint.h>
#include <assert.h>
uint32_t xdj_beta_key_note(uint32_t,uint32_t);
int main(void) {
    uint32_t upper, flag;
    const unsigned normal[]={4,47,101,104,107,110};
    const unsigned green[]={91,96,102,105,108,111};
    unsigned i;
    for(upper=0;upper<256;upper++) for(flag=0;flag<3;flag++) {
        for(i=0;i<6;i++) {
            assert(xdj_beta_key_note((upper<<8)|normal[i],flag)==((upper<<8)|(flag==1?green[i]:normal[i])));
            assert(xdj_beta_key_note((upper<<8)|green[i],flag)==((upper<<8)|(flag==1?green[i]:normal[i])));
        }
        assert(xdj_beta_key_note((upper<<8)|90,flag)==((upper<<8)|90));
        assert(xdj_beta_key_note((upper<<8)|15,flag)==((upper<<8)|15));
    }
    assert(xdj_beta_key_note(4,0xffffffff)==4);
    assert(xdj_beta_key_note(5,0)==5 && xdj_beta_key_note(5,1)==91);
    assert(xdj_beta_key_note(48,0)==48 && xdj_beta_key_note(48,1)==96);
    return 0;
}
