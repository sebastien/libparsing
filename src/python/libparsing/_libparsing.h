/* Additional header file required by CFFI */

typedef char bool;

/* PCRE */
struct real_pcre;
typedef struct real_pcre pcre;

struct real_pcre16;
typedef struct real_pcre16 pcre16;

struct real_pcre32;
typedef struct real_pcre32 pcre32;

struct real_pcre_jit_stack;
typedef struct real_pcre_jit_stack pcre_jit_stack;

struct real_pcre16_jit_stack;
typedef struct real_pcre16_jit_stack pcre16_jit_stack;

struct real_pcre32_jit_stack;
typedef struct real_pcre32_jit_stack pcre32_jit_stack;
typedef struct pcre_extra {
  unsigned long int flags;
  void *study_data;
  unsigned long int match_limit;
  void *callout_data;
  const unsigned char *tables;
  unsigned long int match_limit_recursion;
  unsigned char **mark;
  void *executable_jit;
} pcre_extra;



typedef struct pcre16_extra {
  unsigned long int flags;
  void *study_data;
  unsigned long int match_limit;
  void *callout_data;
  const unsigned char *tables;
  unsigned long int match_limit_recursion;
  unsigned short **mark;
  void *executable_jit;
} pcre16_extra;



typedef struct pcre32_extra {
  unsigned long int flags;
  void *study_data;
  unsigned long int match_limit;
  void *callout_data;
  const unsigned char *tables;
  unsigned long int match_limit_recursion;
  unsigned int **mark;
  void *executable_jit;
} pcre32_extra;






typedef struct pcre_callout_block {
  int version;

  int callout_number;
  int *offset_vector;
  const char * subject;
  int subject_length;
  int start_match;
  int current_position;
  int capture_top;
  int capture_last;
  void *callout_data;

  int pattern_position;
  int next_item_length;

  const unsigned char *mark;

} pcre_callout_block;



typedef struct pcre16_callout_block {
  int version;

  int callout_number;
  int *offset_vector;
  const unsigned short * subject;
  int subject_length;
  int start_match;
  int current_position;
  int capture_top;
  int capture_last;
  void *callout_data;

  int pattern_position;
  int next_item_length;

  const unsigned short *mark;

} pcre16_callout_block;



typedef struct pcre32_callout_block {
  int version;

  int callout_number;
  int *offset_vector;
  const unsigned int * subject;
  int subject_length;
  int start_match;
  int current_position;
  int capture_top;
  int capture_last;
  void *callout_data;

  int pattern_position;
  int next_item_length;

  const unsigned int *mark;

} pcre32_callout_block;
extern void *(*pcre_malloc)(size_t);
extern void (*pcre_free)(void *);
extern void *(*pcre_stack_malloc)(size_t);
extern void (*pcre_stack_free)(void *);
extern int (*pcre_callout)(pcre_callout_block *);
extern int (*pcre_stack_guard)(void);

extern void *(*pcre16_malloc)(size_t);
extern void (*pcre16_free)(void *);
extern void *(*pcre16_stack_malloc)(size_t);
extern void (*pcre16_stack_free)(void *);
extern int (*pcre16_callout)(pcre16_callout_block *);
extern int (*pcre16_stack_guard)(void);

extern void *(*pcre32_malloc)(size_t);
extern void (*pcre32_free)(void *);
extern void *(*pcre32_stack_malloc)(size_t);
extern void (*pcre32_stack_free)(void *);
extern int (*pcre32_callout)(pcre32_callout_block *);
extern int (*pcre32_stack_guard)(void);
typedef pcre_jit_stack *(*pcre_jit_callback)(void *);
typedef pcre16_jit_stack *(*pcre16_jit_callback)(void *);
typedef pcre32_jit_stack *(*pcre32_jit_callback)(void *);



extern pcre *pcre_compile(const char *, int, const char **, int *,
                  const unsigned char *);
extern pcre16 *pcre16_compile(const unsigned short *, int, const char **, int *,
                  const unsigned char *);
extern pcre32 *pcre32_compile(const unsigned int *, int, const char **, int *,
                  const unsigned char *);
extern pcre *pcre_compile2(const char *, int, int *, const char **,
                  int *, const unsigned char *);
extern pcre16 *pcre16_compile2(const unsigned short *, int, int *, const char **,
                  int *, const unsigned char *);
extern pcre32 *pcre32_compile2(const unsigned int *, int, int *, const char **,
                  int *, const unsigned char *);
extern int pcre_config(int, void *);
extern int pcre16_config(int, void *);
extern int pcre32_config(int, void *);
extern int pcre_copy_named_substring(const pcre *, const char *,
                  int *, int, const char *, char *, int);
extern int pcre16_copy_named_substring(const pcre16 *, const unsigned short *,
                  int *, int, const unsigned short *, unsigned short *, int);
extern int pcre32_copy_named_substring(const pcre32 *, const unsigned int *,
                  int *, int, const unsigned int *, unsigned int *, int);
extern int pcre_copy_substring(const char *, int *, int, int,
                  char *, int);
extern int pcre16_copy_substring(const unsigned short *, int *, int, int,
                  unsigned short *, int);
extern int pcre32_copy_substring(const unsigned int *, int *, int, int,
                  unsigned int *, int);
extern int pcre_dfa_exec(const pcre *, const pcre_extra *,
                  const char *, int, int, int, int *, int , int *, int);
extern int pcre16_dfa_exec(const pcre16 *, const pcre16_extra *,
                  const unsigned short *, int, int, int, int *, int , int *, int);
extern int pcre32_dfa_exec(const pcre32 *, const pcre32_extra *,
                  const unsigned int *, int, int, int, int *, int , int *, int);
extern int pcre_exec(const pcre *, const pcre_extra *, const char *,
                   int, int, int, int *, int);
extern int pcre16_exec(const pcre16 *, const pcre16_extra *,
                   const unsigned short *, int, int, int, int *, int);
extern int pcre32_exec(const pcre32 *, const pcre32_extra *,
                   const unsigned int *, int, int, int, int *, int);
extern int pcre_jit_exec(const pcre *, const pcre_extra *,
                   const char *, int, int, int, int *, int,
                   pcre_jit_stack *);
extern int pcre16_jit_exec(const pcre16 *, const pcre16_extra *,
                   const unsigned short *, int, int, int, int *, int,
                   pcre16_jit_stack *);
extern int pcre32_jit_exec(const pcre32 *, const pcre32_extra *,
                   const unsigned int *, int, int, int, int *, int,
                   pcre32_jit_stack *);
extern void pcre_free_substring(const char *);
extern void pcre16_free_substring(const unsigned short *);
extern void pcre32_free_substring(const unsigned int *);
extern void pcre_free_substring_list(const char **);
extern void pcre16_free_substring_list(const unsigned short * *);
extern void pcre32_free_substring_list(const unsigned int * *);
extern int pcre_fullinfo(const pcre *, const pcre_extra *, int,
                  void *);
extern int pcre16_fullinfo(const pcre16 *, const pcre16_extra *, int,
                  void *);
extern int pcre32_fullinfo(const pcre32 *, const pcre32_extra *, int,
                  void *);
extern int pcre_get_named_substring(const pcre *, const char *,
                  int *, int, const char *, const char **);
extern int pcre16_get_named_substring(const pcre16 *, const unsigned short *,
                  int *, int, const unsigned short *, const unsigned short * *);
extern int pcre32_get_named_substring(const pcre32 *, const unsigned int *,
                  int *, int, const unsigned int *, const unsigned int * *);
extern int pcre_get_stringnumber(const pcre *, const char *);
extern int pcre16_get_stringnumber(const pcre16 *, const unsigned short *);
extern int pcre32_get_stringnumber(const pcre32 *, const unsigned int *);
extern int pcre_get_stringtable_entries(const pcre *, const char *,
                  char **, char **);
extern int pcre16_get_stringtable_entries(const pcre16 *, const unsigned short *,
                  unsigned short **, unsigned short **);
extern int pcre32_get_stringtable_entries(const pcre32 *, const unsigned int *,
                  unsigned int **, unsigned int **);
extern int pcre_get_substring(const char *, int *, int, int,
                  const char **);
extern int pcre16_get_substring(const unsigned short *, int *, int, int,
                  const unsigned short * *);
extern int pcre32_get_substring(const unsigned int *, int *, int, int,
                  const unsigned int * *);
extern int pcre_get_substring_list(const char *, int *, int,
                  const char ***);
extern int pcre16_get_substring_list(const unsigned short *, int *, int,
                  const unsigned short * **);
extern int pcre32_get_substring_list(const unsigned int *, int *, int,
                  const unsigned int * **);
extern const unsigned char *pcre_maketables(void);
extern const unsigned char *pcre16_maketables(void);
extern const unsigned char *pcre32_maketables(void);
extern int pcre_refcount(pcre *, int);
extern int pcre16_refcount(pcre16 *, int);
extern int pcre32_refcount(pcre32 *, int);
extern pcre_extra *pcre_study(const pcre *, int, const char **);
extern pcre16_extra *pcre16_study(const pcre16 *, int, const char **);
extern pcre32_extra *pcre32_study(const pcre32 *, int, const char **);
extern void pcre_free_study(pcre_extra *);
extern void pcre16_free_study(pcre16_extra *);
extern void pcre32_free_study(pcre32_extra *);
extern const char *pcre_version(void);
extern const char *pcre16_version(void);
extern const char *pcre32_version(void);


extern int pcre_pattern_to_host_byte_order(pcre *, pcre_extra *,
                  const unsigned char *);
extern int pcre16_pattern_to_host_byte_order(pcre16 *, pcre16_extra *,
                  const unsigned char *);
extern int pcre32_pattern_to_host_byte_order(pcre32 *, pcre32_extra *,
                  const unsigned char *);
extern int pcre16_utf16_to_host_byte_order(unsigned short *,
                  const unsigned short *, int, int *, int);
extern int pcre32_utf32_to_host_byte_order(unsigned int *,
                  const unsigned int *, int, int *, int);



extern pcre_jit_stack *pcre_jit_stack_alloc(int, int);
extern pcre16_jit_stack *pcre16_jit_stack_alloc(int, int);
extern pcre32_jit_stack *pcre32_jit_stack_alloc(int, int);
extern void pcre_jit_stack_free(pcre_jit_stack *);
extern void pcre16_jit_stack_free(pcre16_jit_stack *);
extern void pcre32_jit_stack_free(pcre32_jit_stack *);
extern void pcre_assign_jit_stack(pcre_extra *,
                  pcre_jit_callback, void *);
extern void pcre16_assign_jit_stack(pcre16_extra *,
                  pcre16_jit_callback, void *);
extern void pcre32_assign_jit_stack(pcre32_extra *,
                  pcre32_jit_callback, void *);
extern void pcre_jit_free_unused_memory(void);
extern void pcre16_jit_free_unused_memory(void);
extern void pcre32_jit_free_unused_memory(void);
