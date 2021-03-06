import os
import sys
sys.path.append('/ark/home/af661/src/utils/')
import utils

import string

import numpy
import scipy
import scipy.stats

import subprocess
import os

from string import upper
from random import randrange
from collections import defaultdict

import networkx as nx
from networkx.algorithms.clique import find_cliques_recursive
import pickle

genomeDirectory = '/grail/genomes/Homo_sapiens/UCSC/hg19/Sequence/Chromosomes/'

projectFolder = '/crusader/projects/cll/final/network/extended/node-SE/'
projectName = 'MEC1'
utils.formatFolder(projectFolder + projectName, True)
projectFolder = projectFolder + projectName + '/'

# First, load in the node TFs, ATAC peaks and super enhancer regions we'll consider for this analysis
# From networks already constructed from CRC2.py

node_file = '/crusader/projects/cll/final/network/lines/zinba/' + projectName + '/' + projectName + '_NODELIST.txt'
node_table = utils.parseTable(node_file, '\t')
nodelist = [x[0] for x in node_table]
print nodelist
super_enhancer_file = '/crusader/projects/cll/final/rose/' + projectName + '_H3K27ac/' + projectName + '_H3K27ac_peaks_SuperEnhancers.table.txt'

se_table = utils.parseTable(super_enhancer_file, '\t')

subpeak_file = '/crusader/projects/cll/final/zinba/lines/MEC1_ATAC/MEC1_ATAC.peaks.bed'
subpeak_table = utils.parseTable(subpeak_file, '\t')
subpeak_loci = []
for line in subpeak_table:
    subpeak_loci.append(utils.Locus(line[0], line[1], line[2], '.'))
subpeak_collection = utils.LocusCollection(subpeak_loci, 100)
subpeak_dict = {} # key is enhancer ID, points to a list of loci

# assign subpeak Loci to each super enhancer
fasta = []
se_namelist = []
for line in se_table[6:]:

    se_id = line[0]
    se_namelist.append(se_id)
    subpeak_dict[se_id] = []
    
    se_locus = utils.Locus(line[1], line[2], line[3], '.')
    overlaps = subpeak_collection.getOverlap(se_locus)

    for overlap in overlaps:
        subpeak_dict[se_id].append(overlap)

        subpeak = overlap
        
        fastaTitle = se_id + '|'  + subpeak.chr() + '|' + str(subpeak.start()) + '|' + str(subpeak.end())
        fastaLine = utils.fetchSeq(genomeDirectory, subpeak.chr(), int(subpeak.start()+1), int(subpeak.end()+1))

        fasta.append('>' + fastaTitle)
        fasta.append(upper(fastaLine))


outname = projectFolder + projectName + '_SUBPEAKS.fa'
utils.unParseTable(fasta, outname, '')


# call FIMO and find the motifs within each enhancer

motifConvertFile = '/ark/home/af661/src/coreTFnetwork/annotations/MotifDictionary.txt'
motifDatabaseFile = '/ark/home/af661/src/coreTFnetwork/annotations/VertebratePWMs.txt'

motifDatabase = utils.parseTable(motifConvertFile, '\t')
motifDatabaseDict = {}
motifNames = [line[1] for line in motifDatabase]
for line in motifDatabase:
    motifDatabaseDict[line[1]] = []
for line in motifDatabase:
    motifDatabaseDict[line[1]].append(line[0])

canidateMotifs = []
for gene in nodelist:
    if gene in motifNames:
        canidateMotifs.append(gene)

print canidateMotifs

bgCmd = 'fasta-get-markov -m 1 < ' + projectFolder + projectName + '_SUBPEAKS.fa > ' + projectFolder + projectName + '_bg.meme'
subprocess.call(bgCmd, shell=True)

utils.formatFolder(projectFolder + 'FIMO/', True)

fimoCmd = 'fimo'
for TF in canidateMotifs:
    print TF
    for x in motifDatabaseDict[TF]:
        fimoCmd += ' --motif ' + "'%s'" % (str(x))

#fimoCmd += ' --thresh 1e-5'
fimoCmd += ' -verbosity 1'  # thanks for that ;)!
fimoCmd += ' -text'
fimoCmd += ' -oc ' + projectFolder + 'FIMO'
fimoCmd += ' --bgfile ' + projectFolder + projectName + '_bg.meme'
fimoCmd += ' ' + motifDatabaseFile + ' '
fimoCmd += projectFolder + projectName + '_SUBPEAKS.fa'
fimoCmd += ' > '+ projectFolder + 'FIMO/fimo.txt'  ##
print fimoCmd

fimoOutput = subprocess.call(fimoCmd, shell=True)  #will wait that fimo is done to go on


# next, build a dictionary with all network info and output a matrix with the same information

motifDatabase = utils.parseTable(motifConvertFile, '\t')
motifDatabaseDict = {}
motifNames = [line[1] for line in motifDatabase]

# The reverse of the other dict, from motif name to gene name
for line in motifDatabase:
    motifDatabaseDict[line[0]] = line[1]

fimoFile =  projectFolder + 'FIMO/fimo.txt'
fimoTable = utils.parseTable(fimoFile, '\t')

motifDict = defaultdict(dict)
for line in fimoTable[1:]:

    source = motifDatabaseDict[line[0]]   #motifId
    region = line[1].split('|')
    target = region[0]   #gene name corresponding to the NMid

    if target not in motifDict[source]:
        motifDict[source][target] = 0
    motifDict[source][target] += 1

# make matrix
matrix = [se_namelist]
for tf in motifDict:

    newline = [tf]
    
    for se_id in se_namelist:

        if se_id in motifDict[tf]:
            newline.append(motifDict[tf][se_id])
        else:
            newline.append(0)
    matrix.append(newline)

matrix_name = projectFolder + projectName + '_extendedNetwork.allEnhancers.matrix.txt'
utils.unParseTable(matrix, matrix_name, '\t')
