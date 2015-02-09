# Why
We want distinct databases versioned by date rather than incremental updates
via `update_blastdb.pl`. Something like:
```
/home/jmbrown/blast
├── 2015-02-01
│   ├── nr.nhr
│   ├── nr.nin
│   └── nr.nnd
├── 2015-01-01
│   ├── nr.nhr
│   ├── nr.nin
│   └── nr.nnd
├── 2014-12-01
│   ├── nr.nhr
│   ├── nr.nin
│   └── nr.nnd
└── latest -> /home/jmbrown/blast/2015-02-01
```

# Requires
+ python
    + click
+ wget
+ md5sum
+ tar

# Running
```
$ blastdbget -d 16SMicrobial -d est -d taxdb -d gss_annot $HOME/blast
```

Output:
```
Info      : Using /home/jmbrown/blast as parent directory
Info      : Communicating with Blast server
Info      : Found 8 files matching databases: [16SMicrobial, est, taxdb, gss_annot]
Info      : Downloading 8 files
Jobs Ran + Running  [####################################]  100%
Info      : Validating 4 archives
Jobs Ran + Running  [####################################]  100%
Info      : Extracting 4 archives
Jobs Ran + Running  [####################################]  100%
Info      : Cleaning up tar files
Complete  : Files available at /home/jmbrown/blast/latest
```

Note: If you want `blastdbcheck` to fully function, you should be grabbing `-d taxdb`.

Not specifying `-d` will list Blast DBs that are available.

```
$ python blastdbget.py
Info      : Communicating with Blast server
Usage     : Set `-d` to an available database:
16SMicrobial
Representative_Genomes
cdd_delta
env_nr
env_nt
est
est_human
est_mouse
est_others
gss
gss_annot
htgs
human_genomic
...
```

# Results
```
/home/jmbrown/blast
├── 2015-02-09
│   ├── 16SMicrobial.nhr
│   ├── 16SMicrobial.nin
│   ├── 16SMicrobial.nnd
│   ├── 16SMicrobial.nni
│   ├── 16SMicrobial.nog
│   ├── 16SMicrobial.nsd
│   ├── 16SMicrobial.nsi
│   ├── 16SMicrobial.nsq
│   ├── est.nal
│   ├── gss_annot.00.nhr
│   ├── gss_annot.00.nin
│   ├── gss_annot.00.nnd
│   ├── gss_annot.00.nni
│   ├── gss_annot.00.nog
│   ├── gss_annot.00.nsd
│   ├── gss_annot.00.nsi
│   ├── gss_annot.00.nsq
│   ├── gss.nal
│   ├── taxdb.btd
│   └── taxdb.bti
└── latest -> /home/jmbrown/blast/2015-02-09
```

# Finish up
Set `BLASTDB` to `latest`.
```
export BLASTDB=/home/jmbrown/blast/latest
```

We do monthly updates:
```
0 0 1 * * blastdbget -t 8 -d nr -d nt -d taxdb /mnt/databases/NCBI/blast
```
