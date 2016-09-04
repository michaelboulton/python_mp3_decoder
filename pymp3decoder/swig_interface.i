
%module pymp3_c

%{
#define SWIG_FILE_WITH_INIT
#include "lame/lame.h"
%}

/*
 * I can't figure out why this needs to be declared in C before using it in an
 * extend block. The documentation seems to imply you should be able to declare
 * and extend a type at the same time, but it raises all kinds of issues with
 * incomplete types. I also can't just extend the hip_t struct because swig
 * expects a pointer to the struct which causes all kinds of annoying issues
 * with calling hip_decode
 */
%inline %{
typedef struct LameDecoder {
    hip_t gfp;
} LameDecoder;
%}

%extend LameDecoder {

    /*
     * Typemap needs to be declared inside this block because (???)
     */
    %typemap(in) unsigned char* {
      if (!PyByteArray_Check($input)) {
        SWIG_exception_fail(SWIG_TypeError, "in method '" "$symname" "', argument "
                           "$argnum"" of type '" "$type""'");
      }
      $1 = (unsigned char*) PyByteArray_AsString($input);
    }

    LameDecoder(){
        LameDecoder * x = malloc(sizeof(LameDecoder));
        x->gfp = hip_decode_init();
        return x;
    }

    ~LameDecoder(){
        hip_decode_exit($self->gfp);
        free($self);
    }

    int decode_frame(unsigned char*  mp3buf
                   , size_t          begin
                   , size_t          len
                   , size_t          total_read
                   , unsigned char * pcm_l
                   , unsigned char * pcm_r
                   )
    {
        short * pcm_l_begin = &(((short *) pcm_l)[total_read]);
        short * pcm_r_begin = &(((short *) pcm_r)[total_read]);
        unsigned char * mp3_begin = &(mp3buf[begin]);
        return hip_decode1($self->gfp, mp3_begin, len,
            pcm_l_begin, pcm_r_begin);
    }
}


%inline %{
void
interlace_array(unsigned char * uc_left, unsigned char * uc_right, unsigned char * uc_joined, const int num_samples)
{
    int i;

    short * left = (short *) uc_left;
    short * right = (short *) uc_right;
    short * joined = (short *) uc_joined;

    for (i = 0; i < num_samples; i++)
    {
        int jidx = i*2;
        joined[jidx + 0] = left[i];
        joined[jidx + 1] = right[i];
    }
}
%}
