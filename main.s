	.section	__TEXT,__text,regular,pure_instructions
	.globl	_main
	.align	4, 0x90
_main:
	pushl	%ebp
	movl	%esp, %ebp
	subl	$24, %esp
	movl	$10, -12(%ebp)
	movl	$20, -16(%ebp)
	movl	-12(%ebp), %eax
	movl	-16(%ebp), %ecx
	addl	%ecx, %eax
	movl	%eax, -20(%ebp)
	movl	-20(%ebp), %eax
	movl	%esp, %ecx
	movl	%eax, (%ecx)
	call	_print_int_nl
	movl	-12(%ebp), %eax
	movl	%esp, %ecx
	movl	%eax, (%ecx)
	call	_print_int_nl
	movl	-16(%ebp), %eax
	movl	%esp, %ecx
	movl	%eax, (%ecx)
	call	_print_int_nl
	movl	$0, -8(%ebp)
	movl	-8(%ebp), %eax
	movl	%eax, -4(%ebp)
	movl	-4(%ebp), %eax
	addl	$24, %esp
	popl	%ebp
	ret


.subsections_via_symbols
