# Why
`update_blastdb.pl` is single-threaded and Perl. We want something like this in
the end:
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
+ blastdbcheck
+ python with sh

# Running
```
$ blastdbget -d 16SMicrobial -d sts -d taxdb $HOME/blast
```

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
/home/jmbrown/blast/2015-05-04
├── 16SMicrobial.nhr
├── 16SMicrobial.nin
├── 16SMicrobial.nnd
├── 16SMicrobial.nni
├── 16SMicrobial.nog
├── 16SMicrobial.nsd
├── 16SMicrobial.nsi
├── 16SMicrobial.nsq
├── sts.00.nhd
├── sts.00.nhi
├── sts.00.nhr
├── sts.00.nin
├── sts.00.nnd
├── sts.00.nni
├── sts.00.nog
├── sts.00.nsd
├── sts.00.nsi
├── sts.00.nsq
├── sts.nal
├── taxdb.btd
└── taxdb.bti
```

# Finish up
Manually move symlink to latest:
```
ln -s /home/jmbrown/blast/2015-05-04 /home/jmbrown/blast/latest
```

Set `BLASTDB` to `latest`.
```
export BLASTDB=/home/jmbrown/blast/latest
```

We do monthly updates:
```
0 0 1 * * blastdbget -t 8 -d nr -d nt -d taxdb /mnt/databases/NCBI/blast
```
