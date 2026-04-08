; Lisp Parser Test File
; =====================
; Used by lisp_parser.{py,c,ts} examples.

; -- Atoms --

42
-17
3.14
-2.5

hello
foo
+
-
<=
string->number

"hello world"
"with \"escapes\""

; -- Simple S-expressions --

(+ 1 2)
(define x 42)
(display "hello")

; -- Nested expressions --

(define (square x) (* x x))
(let ((a 1) (b 2)) (+ a b))
(if (> x 0) "positive" "non-positive")

; -- Quote shorthand --

'x
'(1 2 3)
'(a b c)

; -- Dotted pairs --

(1 . 2)
(a b . c)

; -- Complex: Fibonacci --

(define (fibonacci n)
  (if (<= n 1)
    n
    (+ (fibonacci (- n 1))
       (fibonacci (- n 2)))))

(fibonacci 10)
