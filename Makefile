all: final

ps: *.tex
	latex paper_SIMD.tex && dvips -t letter -o paper_SIMD.ps  paper_SIMD.dvi

dvi: *.tex
	latex paper_SIMD.tex

pdf: *.tex
	bibtex -min-crossrefs=10 main
	pdflatex -synctex=-1 -shell-escape paper_SIMD.tex paper_SIMD.pdf

bib:
	bibtex -min-crossrefs=10 main

final: *.tex
	pdflatex -synctex=-1 -shell-escape paper_SIMD.tex paper_SIMD.pdf
	bibtex -min-crossrefs=10 main
	pdflatex -synctex=-1 -shell-escape paper_SIMD.tex paper_SIMD.pdf
	pdflatex -synctex=-1 -shell-escape paper_SIMD.tex paper_SIMD.pdf

quick: *.tex
	pdflatex -synctex=-1 -shell-escape paper_SIMD.tex paper_SIMD.pdf

clean:
	rm -rf *.aux *.bbl *.blg *.brf *.log *.out *.toc *.synctex latex.out
