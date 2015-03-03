function Q = genQc_calD(x,y,z,zy,kernel_type,kernel_param)

[ndata, ndim] = size(x);
[z_ndata, z_ndim] = size(z);

z_vec = zeros(z_ndata,ndata,z_ndim);
x_vec = zeros(z_ndata,ndata,z_ndim);

for i=1:z_ndim
    z_vec(:,:,i) = repmat(z(:,i),[1,ndata]);
    x_vec(:,:,i) = repmat(x(:,i)',[z_ndata,1]);
end
zy_vec = repmat(zy,[1,ndata]);

y = repmat(y',[z_ndata,1]);
zy = repmat(zy,[1,ndata]);

K = Kmtx_eval_calD(x_vec,z_vec,kernel_type,kernel_param);
Q = y.* zy.* K;