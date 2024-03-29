from models.gan.utils import *

"""
###############################################################################################
############################### DISCRIMINATORS Architectures ##################################
###############################################################################################
"""


class NLayerDiscriminator(nn.Module):
    def __init__(self, input_nc, ndf=64, n_layers=3, norm_layer=nn.BatchNorm2d, use_bias=False, real_fake=False):
        super(NLayerDiscriminator, self).__init__()
        dis_model = [nn.Conv2d(input_nc, ndf, kernel_size=4, stride=2, padding=1),
                     nn.LeakyReLU(0.2, True)]
        nf_mult = 1
        nf_mult_prev = 1
        for n in range(1, n_layers):
            nf_mult_prev = nf_mult
            nf_mult = min(2 ** n, 8)
            dis_model += [conv_norm_lrelu(
                ndf * nf_mult_prev, ndf * nf_mult, kernel_size=4, stride=2,
                norm_layer=norm_layer, padding=1, bias=use_bias
            )]

        nf_mult_prev = nf_mult
        nf_mult = min(2 ** n_layers, 8)
        dis_model += [conv_norm_lrelu(
            ndf * nf_mult_prev, ndf * nf_mult, kernel_size=4, stride=1,
            norm_layer=norm_layer, padding=1, bias=use_bias
        )]

        self.dis_model = nn.Sequential(*dis_model)

        self.label_out = nn.Conv2d(ndf * nf_mult, 1, kernel_size=4, stride=1, padding=1)

        self.real_fake = real_fake
        if real_fake:
            self.real_fake_out = nn.Conv2d(ndf * nf_mult, 1, kernel_size=4, stride=1, padding=1)

    def forward(self, x):
        x = self.dis_model(x)
        res = self.label_out(x)
        if self.real_fake:
            res = [self.real_fake_out(x), res]
        else:
            res = [None, res]
        return res


class NLayerDiscriminatorSpectral(nn.Module):
    def __init__(self, input_nc, ndf=64, n_layers=3, use_bias=False, real_fake=False, num_classes=4):
        super(NLayerDiscriminatorSpectral, self).__init__()
        dis_model = [
            nn.utils.spectral_norm(nn.Conv2d(input_nc, ndf, kernel_size=4, stride=2, padding=1)),
            nn.LeakyReLU(0.1, True)
        ]
        nf_mult = 1
        nf_mult_prev = 1
        for n in range(1, n_layers):
            nf_mult_prev = nf_mult
            nf_mult = min(2 ** n, 8)
            dis_model += [conv_spectral_lrelu(
                ndf * nf_mult_prev, ndf * nf_mult, kernel_size=4, stride=2,
                padding=1, bias=use_bias
            )]

        nf_mult_prev = nf_mult
        nf_mult = min(2 ** n_layers, 8)
        dis_model += [conv_spectral_lrelu(
            ndf * nf_mult_prev, ndf * nf_mult, kernel_size=4, stride=1,
            padding=1, bias=use_bias
        )]

        self.dis_model = nn.Sequential(*dis_model)

        self.label_out = nn.Conv2d(ndf * nf_mult, num_classes, kernel_size=4, stride=1, padding=1)

        self.real_fake = real_fake
        if real_fake:
            self.real_fake_out = nn.Conv2d(ndf * nf_mult, 1, kernel_size=4, stride=1, padding=1)

    def forward(self, x):
        x = self.dis_model(x)
        res = self.label_out(x)
        if self.real_fake:
            res = [self.real_fake_out(x), res]
        else:
            res = [None, res]
        return res


class PixelDiscriminator(nn.Module):
    def __init__(self, input_nc, ndf=64, norm_layer=nn.BatchNorm2d, use_bias=False):
        super(PixelDiscriminator, self).__init__()
        dis_model = [
            nn.Conv2d(input_nc, ndf, kernel_size=1, stride=1, padding=0),
            nn.LeakyReLU(0.2, True),
            nn.Conv2d(ndf, ndf * 2, kernel_size=1, stride=1, padding=0, bias=use_bias),
            norm_layer(ndf * 2),
            nn.LeakyReLU(0.2, True),
            nn.Conv2d(ndf * 2, 1, kernel_size=1, stride=1, padding=0, bias=use_bias)]

        self.dis_model = nn.Sequential(*dis_model)

    def forward(self, x):
        return self.dis_model(x)

