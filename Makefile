PDF=pdflatex
BIB=bibtex
INDX=makeindex
PDF_ARGS=-interaction nonstopmode
all: clean paper_SIMD.tex
	$(PDF) paper_SIMD.tex
	$(BIB) paper_SIMD
	$(PDF) paper_SIMD.tex
	$(PDF) paper_SIMD.tex
nostop: thespaper_SIMD.tex
	$(PDF) $(PDF_ARGS) paper_SIMD.tex
	$(BIB) paper_SIMD
	$(PDF) $(PDF_ARGS) paper_SIMD.tex
	$(PDF) $(PDF_ARGS) paper_SIMD.tex
clean:
	rm -f *.{ps,log,aux,out,dvi,bbl,blg,idx,ilg,ind,lof,lot,toc}
	rm -f paper_SIMD.pdf


