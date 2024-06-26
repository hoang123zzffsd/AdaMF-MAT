from email.generator import Generator
import torch
import mmkgc
from mmkgc.config import Tester, AdvMixTrainer
from mmkgc.module.model import AdvMixTransE
from mmkgc.module.loss import SigmoidLoss
from mmkgc.module.strategy import NegativeSampling
from mmkgc.data import TrainDataLoader, TestDataLoader
from mmkgc.adv.modules import MultiGenerator

from args import get_args

if __name__ == "__main__":
    args = get_args()
    print(args)
    # set the seed
    torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)
    # dataloader for training
    train_dataloader = TrainDataLoader(
        in_path="/content/AdaMF-MAT/benchmarks/" + args.dataset + '/',
        batch_size=args.batch_size,
        threads=8,
        sampling_mode="normal",
        bern_flag=1,
        filter_flag=1,
        neg_ent=args.neg_num,
        neg_rel=0


    )
    # dataloader for test
    test_dataloader = TestDataLoader(
        "/content/AdaMF-MAT/benchmarks/" + args.dataset + '/', "link")
    img_emb = torch.load('/content/AdaMF-MAT/embeddings/' + args.dataset + '-visual.pth')
    text_emb = torch.load('/content/AdaMF-MAT/embeddings/' + args.dataset + '-textual.pth')
    # define the model
    kge_score = AdvMixTransE(
        ent_tot=train_dataloader.get_ent_tot(),
        rel_tot=train_dataloader.get_rel_tot(),
        dim=args.dim,
        margin=args.margin,
        epsilon=2.0,
        img_emb=img_emb,
        text_emb=text_emb,
        norm_flag=True,
        p_norm=1,

            
    )
    print("kge score:",kge_score)
    # define the loss function
    model = NegativeSampling(
        model=kge_score,
        loss=SigmoidLoss(adv_temperature=args.adv_temp),
        batch_size=train_dataloader.get_batch_size(),
    )
    
    adv_generator = MultiGenerator(
        noise_dim=64,
        structure_dim=args.dim,
        img_dim=args.dim
    )
    # train the model
    trainer = AdvMixTrainer(
        model=model,
        data_loader=train_dataloader,
        train_times=args.epoch,
        alpha=args.learning_rate,
        use_gpu=True,
        opt_method='Adam',
        generator=adv_generator,
        lrg=args.lrg,
        mu=args.mu
    )

    trainer.run()
    kge_score.save_checkpoint(args.save)

    # test the model
    kge_score.load_checkpoint(args.save)
    tester = Tester(model=kge_score, data_loader=test_dataloader, use_gpu=True)
    tester.run_link_prediction(type_constrain=False)
    acc, p, r, f, _ = tester.run_triple_classification_four_metrics()
    print(acc, p, r, f)
